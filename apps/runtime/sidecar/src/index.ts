// apps/runtime/sidecar/src/index.ts
import { createServer, type Socket } from "node:net";
import { existsSync, unlinkSync } from "node:fs";
import {
  parseMessage,
  serializeMessage,
  type InboundMessage,
  type PiEvent,
  type InvokeRequest,
} from "./protocol.js";
import { SidecarSessionManager } from "./session-manager.js";

const SOCKET_PATH = process.env.PIAGENT_SOCKET_PATH ?? "/tmp/piagent.sock";
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

async function main() {
  if (existsSync(SOCKET_PATH)) {
    unlinkSync(SOCKET_PATH);
  }

  const server = createServer((socket: Socket) => {
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

  process.on("SIGTERM", async () => {
    await sessionManager.destroyAll();
    server.close();
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
