// apps/runtime/sidecar/src/protocol.ts

export type ThinkingLevel = "off" | "minimal" | "low" | "medium" | "high" | "xhigh";

export interface AgentTool {
  name: string;
  description?: string;
  input_schema?: Record<string, unknown>;
  execute?: (toolCallId: string, params: Record<string, unknown>) => Promise<unknown>;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface InvokeRequest {
  type: "invoke";
  id: string;
  session_id?: string;
  message: string;
  tools?: AgentTool[];
  model?: string;
  thinking_level?: ThinkingLevel;
}

export interface PingRequest {
  type: "ping";
}

export interface ShutdownRequest {
  type: "shutdown";
}

export type InboundMessage = InvokeRequest | PingRequest | ShutdownRequest;

export type PiEventType =
  | "agent_start"
  | "turn_start"
  | "message_start"
  | "message_update"
  | "message_end"
  | "tool_execution_start"
  | "tool_execution_update"
  | "tool_execution_end"
  | "turn_end"
  | "agent_end";

export interface PiEvent {
  type: PiEventType;
  [key: string]: unknown;
}

export interface EventResponse {
  type: "event";
  request_id: string;
  event: PiEvent;
}

export interface ResultResponse {
  type: "result";
  request_id: string;
  result: {
    answer: string;
    session_id: string;
    tool_calls: ToolCall[];
    total_tokens: number;
    cost: number;
    duration_ms: number;
  };
}

export interface ErrorResponse {
  type: "error";
  request_id: string;
  error: string;
  detail?: string;
}

export interface PongResponse {
  type: "pong";
  uptime: number;
}

export type OutboundMessage = EventResponse | ResultResponse | ErrorResponse | PongResponse;

export function parseMessage(line: string): InboundMessage {
  if (!line.trim()) throw new Error("Empty line");
  return JSON.parse(line) as InboundMessage;
}

export function serializeMessage(msg: OutboundMessage): string {
  return JSON.stringify(msg) + "\n";
}
