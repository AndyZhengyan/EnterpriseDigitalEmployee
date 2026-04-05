// apps/runtime/sidecar/src/session-manager.ts
import {
  createAgentSession,
  type AgentSession,
  AuthStorage,
  ModelRegistry,
} from "@mariozechner/pi-coding-agent";
import { getModel } from "@mariozechner/pi-ai";

const MAX_SESSIONS = 100;

// Default to MiniMax China region (api.minimaxi.com) for best compatibility.
const DEFAULT_MODEL = getModel("minimax-cn", "MiniMax-M2.7");

interface PooledSession {
  session: AgentSession;
  lastUse: number;
}

export class SidecarSessionManager {
  private sessions = new Map<string, PooledSession>();
  private defaultSession?: AgentSession;

  async getOrCreate(sessionId?: string, model?: ReturnType<typeof getModel>): Promise<AgentSession> {
    if (sessionId) {
      const pooled = this.sessions.get(sessionId);
      if (pooled) {
        pooled.lastUse = Date.now();
        return pooled.session;
      }
    }

    const authStorage = AuthStorage.create();
    const { session } = await createAgentSession({
      authStorage,
      modelRegistry: new ModelRegistry(authStorage),
      model: model ?? DEFAULT_MODEL,
    });

    if (sessionId) {
      this.evictIfNeeded();
      this.sessions.set(sessionId, { session, lastUse: Date.now() });
    } else if (!this.defaultSession) {
      this.defaultSession = session;
    }

    return session;
  }

  private evictIfNeeded(): void {
    if (this.sessions.size >= MAX_SESSIONS) {
      let oldestKey: string | null = null;
      let oldestTime = Infinity;
      for (const [key, val] of this.sessions) {
        if (val.lastUse < oldestTime) {
          oldestTime = val.lastUse;
          oldestKey = key;
        }
      }
      if (oldestKey) this.sessions.delete(oldestKey);
    }
  }

  async destroy(sessionId: string): Promise<void> {
    this.sessions.delete(sessionId);
  }

  async destroyAll(): Promise<void> {
    this.sessions.clear();
    this.defaultSession = undefined;
  }

  get size(): number {
    return this.sessions.size;
  }
}
