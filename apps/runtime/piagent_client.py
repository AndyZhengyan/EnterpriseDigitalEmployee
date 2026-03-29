"""PiAgent 客户端

包装 OpenClaw Gateway 的 `openclaw agent` CLI，实现与 PiAgent 的通信。

集成方式：
- 优先：HTTP/WebSocket API（Gateway 的 agent 调用接口）
- 回退：subprocess 调用 `openclaw agent --json` CLI

规格依据：specs/runtime-spec.md - Runtime 与 PiAgent 集成
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("runtime.piagent")


# ============== 错误定义 ==============


class PiAgentError(Exception):
    """PiAgent 调用错误"""

    def __init__(self, message: str, agent_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.agent_id = agent_id
        self.details = details or {}


class PiAgentTimeoutError(PiAgentError):
    """PiAgent 调用超时"""

    pass


class PiAgentAuthError(PiAgentError):
    """PiAgent 认证失败"""

    pass


# ============== 结果模型 ==============


@dataclass
class PiAgentResult:
    """PiAgent 执行结果"""

    run_id: str
    status: str  # ok | error
    summary: str
    text: Optional[str] = None
    media_url: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: int = 0
    usage: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PiAgentResult":
        """从字典构造结果"""
        result = data.get("result", {})
        payloads = result.get("payloads", [])
        first_text = None
        first_media = None
        for p in payloads:
            if p.get("text"):
                first_text = p["text"]
                break
            if p.get("mediaUrl"):
                first_media = p["mediaUrl"]
                break

        return cls(
            run_id=data.get("runId", ""),
            status=data.get("status", "unknown"),
            summary=data.get("summary", ""),
            text=first_text,
            media_url=first_media,
            session_id=result.get("meta", {}).get("agentMeta", {}).get("sessionId"),
            duration_ms=result.get("meta", {}).get("durationMs", 0),
            usage=result.get("meta", {}).get("agentMeta", {}).get("usage", {}),
            meta=result.get("meta", {}),
            raw=data,
        )


# ============== PiAgent 客户端 ==============


class PiAgentClient:
    """
    PiAgent 客户端。

    通过 OpenClaw Gateway 调用 Agent。

    支持的 Agent：
    - chat: 前台调度（小虾米）- 默认
    - deep-work: 深度专家（小龙）
    - super-work: 超级专家（大龙）

    使用 subprocess 调用 `openclaw agent` CLI 实现。
    """

    DEFAULT_AGENT = "chat"
    GATEWAY_PORT = 18789

    @classmethod
    def _get_token(cls) -> str:
        """从环境变量或配置文件读取 Gateway token"""
        import os

        token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        if token:
            return token
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        try:
            with open(config_path) as f:
                cfg = json.load(f)
                return cfg.get("gateway", {}).get("auth", {}).get("token", "")
        except FileNotFoundError:
            raise PiAgentError(
                f"OpenClaw config not found at {config_path}. Run `openclaw gateway init` to configure.",
                agent_id=None,
            )
        except json.JSONDecodeError as e:
            raise PiAgentError(
                f"Invalid OpenClaw config at {config_path}: {e}",
                agent_id=None,
            )
        except KeyError:
            raise PiAgentError(
                f"OpenClaw config at {config_path} is missing 'gateway.auth.token' field.",
                agent_id=None,
            )

    def __init__(
        self,
        agent_id: str = DEFAULT_AGENT,
        timeout_seconds: int = 300,
        thinking_level: str = "medium",
        gateway_token: Optional[str] = None,
        gateway_port: Optional[int] = None,
    ):
        self.agent_id = agent_id
        self.timeout_seconds = timeout_seconds
        self.thinking_level = thinking_level
        self.gateway_token = gateway_token or self.GATEWAY_TOKEN
        self.gateway_port = gateway_port or self.GATEWAY_PORT

    def _build_cli_args(self, message: str, session_id: Optional[str] = None) -> List[str]:
        """构建 openclaw agent CLI 参数"""
        args = [
            "openclaw",
            "agent",
            "--agent",
            self.agent_id,
            "--message",
            message,
            "--json",
            "--thinking",
            self.thinking_level,
            "--timeout",
            str(self.timeout_seconds),
        ]
        if session_id:
            args.extend(["--session-id", session_id])
        return args

    def _get_gateway_url(self) -> str:
        """
        获取 Gateway URL（用于环境变量）

        Note: Always use https:// in production. HTTP is only acceptable
        on localhost (127.0.0.1). When deploying, ensure OPENCLAW_GATEWAY_URL
        uses https:// and the TLS certificate is valid.
        """
        return f"http://127.0.0.1:{self.gateway_port}"

    def invoke(self, message: str, session_id: Optional[str] = None) -> PiAgentResult:
        """
        同步调用 PiAgent。

        Args:
            message: 要发送给 Agent 的消息
            session_id: 可选的会话 ID（用于保持上下文）

        Returns:
            PiAgentResult: 执行结果

        Raises:
            PiAgentError: 调用失败
            PiAgentTimeoutError: 超时
            PiAgentAuthError: 认证失败
        """
        cli_args = self._build_cli_args(message, session_id)
        env = {
            **subprocess.os.environ,
            "OPENCLAW_GATEWAY_TOKEN": self.gateway_token,
            "OPENCLAW_GATEWAY_URL": self._get_gateway_url(),
        }

        log = logger.bind(
            agent_id=self.agent_id,
            session_id=session_id,
            message_preview=message[:100],
        )
        log.info("piagent_invoke_start", cli=" ".join(cli_args[:5]))

        try:
            result = subprocess.run(
                cli_args,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=env,
                check=False,  # 我们自己处理返回码
            )

            if result.returncode != 0:
                # 解析错误
                stderr = result.stderr.strip()
                if "timeout" in stderr.lower() or "timed out" in stderr.lower():
                    raise PiAgentTimeoutError(
                        f"Agent invocation timed out after {self.timeout_seconds}s",
                        agent_id=self.agent_id,
                    )
                if "auth" in stderr.lower() or "401" in stderr or "token" in stderr.lower():
                    raise PiAgentAuthError(
                        f"Authentication failed: {stderr[:200]}",
                        agent_id=self.agent_id,
                    )
                raise PiAgentError(
                    f"Agent invocation failed (exit {result.returncode}): {stderr[:500]}",
                    agent_id=self.agent_id,
                    details={"stderr": stderr, "returncode": result.returncode},
                )

            # 解析 JSON 输出
            stdout = result.stdout.strip()
            if not stdout:
                raise PiAgentError(
                    "Empty response from agent",
                    agent_id=self.agent_id,
                )

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as e:
                raise PiAgentError(
                    f"Invalid JSON from agent: {e}",
                    agent_id=self.agent_id,
                    details={"stdout_preview": stdout[:500]},
                )

            piagent_result = PiAgentResult.from_dict(data)
            log.info(
                "piagent_invoke_done",
                run_id=piagent_result.run_id,
                status=piagent_result.status,
                duration_ms=piagent_result.duration_ms,
            )
            return piagent_result

        except subprocess.TimeoutExpired:
            raise PiAgentTimeoutError(
                f"Agent invocation timed out after {self.timeout_seconds}s",
                agent_id=self.agent_id,
            )
        except PiAgentError:
            raise
        except FileNotFoundError:
            raise PiAgentError(
                "openclaw CLI not found. Is OpenClaw installed and in PATH?",
                agent_id=self.agent_id,
            )
        except Exception as e:
            logger.error("piagent_invoke_error", error=str(e), error_type=type(e).__name__)
            raise PiAgentError(str(e), agent_id=self.agent_id)

    def invoke_async(self, message: str, session_id: Optional[str] = None) -> PiAgentResult:
        """
        异步调用 PiAgent（内部使用 subprocess.Popen）。

        Returns:
            PiAgentResult: 需在外部调用 result.wait() 并通过 stdout 读取结果
        """
        cli_args = self._build_cli_args(message, session_id)
        env = {
            **subprocess.os.environ,
            "OPENCLAW_GATEWAY_TOKEN": self.gateway_token,
            "OPENCLAW_GATEWAY_URL": self._get_gateway_url(),
        }
        proc = subprocess.Popen(
            cli_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        return proc


# ============== 会话管理器 ==============


class PiAgentSession:
    """
    PiAgent 会话。

    在多个调用之间保持会话上下文。
    """

    def __init__(self, client: PiAgentClient, session_id: Optional[str] = None):
        self.client = client
        self.session_id = session_id or self._new_session_id()
        self.call_count = 0
        self.created_at = datetime.utcnow()

    @staticmethod
    def _new_session_id() -> str:
        """生成新的会话 ID"""
        import uuid

        return str(uuid.uuid4())

    def send(self, message: str) -> PiAgentResult:
        """发送消息到当前会话"""
        self.call_count += 1
        result = self.client.invoke(message, session_id=self.session_id)
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取会话历史。

        TODO: 通过 Gateway API 获取历史消息。
        当前返回内存中的记录。
        """
        # 当前为占位实现
        return []


class PiAgentSessionManager:
    """
    PiAgent 会话管理器。

    管理多个会话的生命周期。
    """

    def __init__(self, default_agent: str = PiAgentClient.DEFAULT_AGENT):
        self.default_agent = default_agent
        self._sessions: Dict[str, PiAgentSession] = {}

    def get_or_create(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> PiAgentSession:
        """获取或创建会话"""
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        client = PiAgentClient(agent_id=agent_id or self.default_agent)
        session = PiAgentSession(client, session_id)
        if session_id:
            self._sessions[session_id] = session
        return session

    def delete(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
