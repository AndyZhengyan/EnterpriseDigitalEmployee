// apps/runtime/sidecar/src/index.ts
import { createServer, type Socket } from "node:net";
import { existsSync, unlinkSync } from "node:fs";
import { parseMessage, serializeMessage, type InboundMessage, type PiEvent } from "./protocol.js";
import { SidecarSessionManager } from "./session-manager.js";

const SOCKET_PATH = process.env.PIAGENT_SOCKET_PATH ?? "/tmp/piagent.sock";
const sessionManager = new SidecarSessionManager();
const startTime = Date.now();

async function handleInvoke(
  socket: Socket,
  requestId: string,
  sessionId: string | undefined,
  message: string,
  _thinkingLevel?: string
) {
  try {
    const session = await sessionManager.getOrCreate(sessionId);

    for await (const event of session.prompt(message) as unknown as AsyncIterable<PiEvent>) {
      const outbound = {
        type: "event" as const,
        request_id: requestId,
        event: JSON.parse(JSON.stringify(event)),
      };
      socket.write(serializeMessage(outbound));
    }

    // 从 session.state.messages 取最后一个 assistant 消息
    const messages = (session as unknown as { state: { messages: Array<{role: string; content: string}> } }).state?.messages ?? [];
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    const answer = lastAssistant?.content ?? "";

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

  const server = createServer((socket) => {
    let buffer = "";

    socket.on("data", async (chunk) => {
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
            await handleInvoke(socket, msg.id, msg.session_id, msg.message, msg.thinking_level);
          }
        } catch (err) {
          const errMsg = err instanceof Error ? err.message : String(err);
          socket.write(serializeMessage({ type: "error", request_id: "", error: "PARSE_ERROR", detail: errMsg }));
        }
      }
    });

    socket.on("error", (err) => {
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
