// apps/runtime/sidecar/src/index.ts
import { createServer as createNetServer, type Socket } from "node:net";
import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from "node:http";
import { existsSync, unlinkSync } from "node:fs";
import {
  parseMessage,
  serializeMessage,
  type InboundMessage,
  type PiEvent,
  type InvokeRequest,
} from "./protocol.js";
import { SidecarSessionManager } from "./session-manager.js";
import { getModel, type KnownProvider } from "@mariozechner/pi-ai";

const SOCKET_PATH = process.env.PIAGENT_SOCKET_PATH ?? "/tmp/piagent.sock";
const HTTP_PORT = Number(process.env.PIAGENT_HTTP_PORT ?? 8090);
const sessionManager = new SidecarSessionManager();
const startTime = Date.now();

interface AssistantMessage {
  role: string;
  content: Array<{ type: string; text?: string }>;
}

async function handleInvoke(
  socket: Socket,
  request: InvokeRequest
) {
  const { id: requestId, session_id: sessionId, message } = request;

  try {
    const session = await sessionManager.getOrCreate(sessionId);

    // Accumulate assistant text from streaming text_delta events.
    // Some providers (e.g. MiniMax) send text via deltas without populating
    // the final message.content array, so we must gather deltas directly.
    let accumulatedText = "";

    const unsubscribe = session.agent.subscribe(async (event: PiEvent) => {
      const ev = event as { type: string; assistantMessageEvent?: { type: string; delta?: string } };
      if (ev.type === "message_update" && ev.assistantMessageEvent?.type === "text_delta") {
        accumulatedText += ev.assistantMessageEvent.delta ?? "";
      }

      const outbound = {
        type: "event" as const,
        request_id: requestId,
        event: JSON.parse(JSON.stringify(event)),
      };
      socket.write(serializeMessage(outbound));
    });

    try {
      await session.prompt(message);
    } finally {
      unsubscribe();
    }

    // Fall back to session.state.messages if no delta text was accumulated.
    // message.content is Array<{type: string; text?: string}>, not plain string.
    let answer = accumulatedText;
    if (!answer) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const state = (session as any).state as { messages: AssistantMessage[] } | undefined;
      const messages = state?.messages ?? [];
      const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
      if (lastAssistant?.content) {
        answer = lastAssistant.content
          .filter((c) => c.type === "text")
          .map((c) => c.text ?? "")
          .join("");
      }
    }

    socket.write(serializeMessage({
      type: "result" as const,
      request_id: requestId,
      result: {
        answer,
        session_id: sessionId ?? "default",
        tool_calls: [],
        total_tokens: 0,
        cost: 0,
        duration_ms: 0,
      },
    }));
  } catch (err: unknown) {
    const error = err instanceof Error ? err : new Error(String(err));
    socket.write(serializeMessage({
      type: "error" as const,
      request_id: requestId,
      error: error.constructor.name,
      detail: error.message,
    }));
  }
}

// ---------------------------------------------------------------------------
// HTTP server handlers
// ---------------------------------------------------------------------------

function readJsonBody<T>(req: IncomingMessage): Promise<T> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()) as T);
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function extractText(content: string | Array<{ type: string; text?: string }>): string {
  if (typeof content === "string") return content;
  return (content as Array<{ type: string; text?: string }>)
    .filter((b) => b.type === "text")
    .map((b) => b.text ?? "")
    .join("");
}

function messagesToString(
  messages: Array<{ role: string; content: string | Array<{ type: string; text?: string }> }>
): string {
  return messages
    .map((m) => `${m.role}: ${extractText(m.content)}`)
    .join("\n");
}

async function handleHealth(res: ServerResponse): Promise<void> {
  sendJson(res, 200, { status: "ok", uptime: Date.now() - startTime });
}

interface ChatRequest {
  provider: string;
  model: string;
  messages: Array<{ role: string; content: string | Array<{ type: string; text?: string }> }>;
  session_id?: string;
  thinking_level?: string;
  temperature?: number;
}

async function handleChat(
  req: IncomingMessage,
  res: ServerResponse
): Promise<void> {
  let body: ChatRequest;
  try {
    body = await readJsonBody<ChatRequest>(req);
  } catch {
    sendJson(res, 400, { error: "Invalid JSON body", code: "BAD_REQUEST" });
    return;
  }

  const { provider, model, messages, session_id: sessionId } = body;

  if (!provider || !model || !Array.isArray(messages)) {
    sendJson(res, 400, { error: "Missing required fields: provider, model, messages", code: "BAD_REQUEST" });
    return;
  }

  let modelInstance: ReturnType<typeof getModel>;
  try {
    // getModel is a generic function requiring literal string types for inference.
    // User input is validated at runtime inside the try block, so we cast through unknown.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    modelInstance = getModel(provider as any, model as any);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    sendJson(res, 400, { error: `Unknown model: ${msg}`, code: "INVALID_MODEL" });
    return;
  }

  try {
    const session = await sessionManager.getOrCreate(sessionId, modelInstance);
    const requestStart = Date.now();

    let accumulatedText = "";
    let usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | undefined;
    let finishReason: string | undefined;

    const unsubscribe = session.agent.subscribe(async (event: PiEvent) => {
      const ev = event as Record<string, unknown>;

      if (ev.type === "message_update") {
        const assistantMessageEvent = (ev.assistantMessageEvent ?? ev.delta) as Record<string, unknown> | undefined;
        if (assistantMessageEvent?.type === "text_delta" && typeof assistantMessageEvent.delta === "string") {
          accumulatedText += assistantMessageEvent.delta;
        }
      }

      if (ev.type === "agent_end") {
        const msgObj = ev.message as Record<string, unknown> | undefined;
        usage = msgObj?.usage as typeof usage;
        finishReason = (msgObj?.stop_reason ?? msgObj?.finish_reason) as string | undefined;
      }
    });

    try {
      await session.prompt(messagesToString(messages));
    } finally {
      unsubscribe();
    }

    sendJson(res, 200, {
      content: accumulatedText,
      model,
      provider,
      usage: usage ?? { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      finish_reason: finishReason ?? "stop",
      latency_ms: Date.now() - requestStart,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    sendJson(res, 500, { error: msg, code: "PROVIDER_ERROR" });
  }
}

async function main() {
  if (existsSync(SOCKET_PATH)) {
    unlinkSync(SOCKET_PATH);
  }

  const server = createNetServer((socket: Socket) => {
    let buffer = "";

    socket.on("data", async (chunk: Buffer) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const rawLine of lines) {
        if (!rawLine.trim()) continue;
        try {
          const msg = parseMessage(rawLine) as InboundMessage;

          if (msg.type === "ping") {
            socket.write(serializeMessage({ type: "pong", uptime: Date.now() - startTime }));
            continue;
          }

          if (msg.type === "shutdown") {
            socket.end();
            return;
          }

          if (msg.type === "invoke") {
            await handleInvoke(socket, msg);
          }
        } catch (err) {
          const errMsg = err instanceof Error ? err.message : String(err);
          socket.write(serializeMessage({ type: "error", request_id: "", error: "PARSE_ERROR", detail: errMsg }));
        }
      }
    });

    socket.on("error", (err: Error) => {
      console.error("Socket error:", err.message);
    });
  });

  server.listen(SOCKET_PATH, () => {
    console.log(`PiAgent sidecar listening on ${SOCKET_PATH}`);
  });

  const httpServer = createHttpServer(async (req: IncomingMessage, res: ServerResponse) => {
    try {
      if (req.method === "GET" && req.url === "/health") {
        await handleHealth(res);
        return;
      }
      if (req.method === "POST" && req.url === "/chat") {
        await handleChat(req, res);
        return;
      }
      sendJson(res, 404, { error: "Not Found", code: "NOT_FOUND" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("HTTP handler error:", msg);
      sendJson(res, 500, { error: "Internal server error", code: "INTERNAL_ERROR" });
    }
  });

  httpServer.listen(HTTP_PORT, () => {
    console.log(`PiAgent sidecar HTTP server listening on port ${HTTP_PORT}`);
  });

  process.on("SIGTERM", async () => {
    await sessionManager.destroyAll();
    server.close();
    httpServer.close();
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
