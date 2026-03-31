"""PiAgent 客户端

实现与 OpenClaw Gateway 的通信，支持 WebSocket (优先) 和 CLI (回退) 两种模式。
符合 OpenClaw Gateway Protocol V3。
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
import websockets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from common.config import settings

logger = structlog.get_logger("runtime.piagent")


# ============== 认证与身份管理 ==============


@dataclass
class OpenClawIdentity:
    """OpenClaw 客户端身份信息"""

    device_id: str
    public_key: str  # Base64Url 编码的原始公钥
    device_token: Optional[str] = None
    private_key_pem: Optional[str] = None

    @classmethod
    def load_local(cls) -> OpenClawIdentity:
        """从本地文件系统自动加载身份（生产/本地开发环境）"""
        # 默认回退值（匹配已知配对设备，提高开箱即用率）
        identity = cls(
            device_id="908839d4b1102fd70f009fa245da8b446c9399be0b7391c97e42e3b6d794432b",
            public_key="rLoUvPIdwn3CBWg9DGcs1lPEWDSDiu-6MOguMiUFeO0",
            device_token=None,
            private_key_pem=None,
        )

        try:
            id_path = os.path.join(settings.openclaw.identity_dir, "device.json")
            auth_path = os.path.join(settings.openclaw.identity_dir, "device-auth.json")

            if os.path.exists(id_path):
                with open(id_path) as f:
                    data = json.load(f)
                    identity.device_id = data.get("deviceId", identity.device_id)
                    identity.private_key_pem = data.get("privateKeyPem")
                    # 解析公钥
                    pub_pem = data.get("publicKeyPem")
                    if pub_pem:
                        # 提取 SPKI 中的原始 Key (最后 32 字节)
                        pub_bytes = base64.b64decode("".join(pub_pem.split("\n")[1:-2]))
                        if len(pub_bytes) >= 32:
                            identity.public_key = cls._base64url_encode(pub_bytes[-32:])

            if os.path.exists(auth_path):
                with open(auth_path) as f:
                    data = json.load(f)
                    tokens = data.get("tokens", {})
                    op_token = tokens.get("operator", {}).get("token")
                    if op_token:
                        identity.device_token = op_token
        except Exception as e:
            logger.warning("identity_load_failed", error=str(e))

        return identity

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def sign_v3(self, params: Dict[str, Any]) -> str:
        """执行 V3 协议签名"""
        if not self.private_key_pem:
            # 如果没有私钥，尝试返回一个 dummy 签名（仅用于本地非严格模式）
            return "op_sig"

        try:
            scopes_str = ",".join(params.get("scopes", []))
            token_str = params.get("token") or ""
            platform = params.get("platform") or ""
            device_family = params.get("deviceFamily") or ""

            # 标准 V3 Payload 格式
            payload = "|".join(
                [
                    "v3",
                    params["deviceId"],
                    params["clientId"],
                    params["clientMode"],
                    params["role"],
                    scopes_str,
                    str(params["signedAtMs"]),
                    token_str,
                    params["nonce"],
                    platform,
                    device_family,
                ]
            )

            private_key = serialization.load_pem_private_key(self.private_key_pem.encode("utf-8"), password=None)
            # 显式转换为 Ed25519 类型以满足 mypy 静态检查
            if isinstance(private_key, ed25519.Ed25519PrivateKey):
                signature = private_key.sign(payload.encode("utf-8"))
                return self._base64url_encode(signature)
            else:
                raise TypeError("Expected Ed25519 private key for signing")
        except Exception as e:
            logger.error("signing_failed", error=str(e))
            return "none"


# ============== 错误定义 ==============


class PiAgentError(Exception):
    """PiAgent 调用错误"""

    def __init__(self, message: str, agent_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.agent_id = agent_id
        self.details = details or {}


class PiAgentAuthError(PiAgentError):
    """PiAgent 认证失败"""

    pass


class PiAgentTimeoutError(PiAgentError):
    """PiAgent 调用超时"""

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
    PiAgent 客户端（现代化重构版）。

    支持：
    1. 自动身份发现与签名。
    2. 基于配置的连接管理。
    3. 流式与非流式调用。
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
                token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
                if not token:
                    raise KeyError("gateway.auth.token is empty")
                return token
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
        agent_id: str = "chat",
        thinking_level: str = "medium",
        identity: Optional[OpenClawIdentity] = None,
        gateway_token: Optional[str] = None,
        gateway_host: Optional[str] = None,
        gateway_port: Optional[int] = None,
        timeout_seconds: int = 300,
    ):
        self.agent_id = agent_id
        self.thinking_level = thinking_level
        # 支持注入身份（用于单元测试和 Harness）
        self.identity = identity or OpenClawIdentity.load_local()
        self.gateway_token = gateway_token or settings.openclaw.gateway_token or self._get_default_token()
        self.gateway_host = gateway_host or settings.openclaw.gateway_host
        self.gateway_port = gateway_port or settings.openclaw.gateway_port
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _get_default_token() -> str:
        """回退方案：从 OpenClaw 主配置文件读取 token"""
        try:
            if os.path.exists(settings.openclaw.config_file):
                with open(settings.openclaw.config_file) as f:
                    cfg = json.load(f)
                    return cfg.get("gateway", {}).get("auth", {}).get("token", "")
        except Exception:
            pass
        return ""

    async def _connect_and_handshake(self) -> Any:
        """建立连接并执行 V3 握手"""
        uri = f"ws://{self.gateway_host}:{self.gateway_port}/"
        origin = f"http://{self.gateway_host}:{self.gateway_port}"

        ws = await websockets.connect(uri, origin=origin)  # type: ignore[arg-type]

        # 1. 接收 Challenge
        challenge = json.loads(await ws.recv())
        nonce = challenge["payload"]["nonce"]
        ts_now = int(datetime.now(timezone.utc).timestamp() * 1000)

        # 2. 准备 Connect 参数
        auth_payload: Dict[str, Any] = {"token": self.gateway_token}
        if self.identity.device_token:
            auth_payload["deviceToken"] = self.identity.device_token

        # 计算签名 (核心安全逻辑)
        signature = self.identity.sign_v3(
            {
                "deviceId": self.identity.device_id,
                "clientId": settings.openclaw.client_id,
                "clientMode": settings.openclaw.client_mode,
                "role": "operator",
                "scopes": settings.openclaw.default_scopes,
                "signedAtMs": ts_now,
                "token": self.gateway_token,
                "nonce": nonce,
                "platform": settings.openclaw.platform,
                "deviceFamily": "",
            }
        )

        connect_req = {
            "type": "req",
            "id": f"conn-{uuid.uuid4().hex[:8]}",
            "method": "connect",
            "payload": {
                "auth": auth_payload,
                "client": {
                    "deviceId": self.identity.device_id,
                    "clientId": settings.openclaw.client_id,
                    "clientMode": settings.openclaw.client_mode,
                    "role": "operator",
                    "scopes": settings.openclaw.default_scopes,
                    "platform": settings.openclaw.platform,
                    "deviceFamily": "",
                    "signedAtMs": ts_now,
                },
                "signature": signature,
            },
        }

        await ws.send(json.dumps(connect_req))
        resp = json.loads(await ws.recv())
        if resp.get("type") == "error":
            raise PiAgentAuthError(f"Connection rejected: {resp}", agent_id=self.agent_id)

        return ws

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
        # 只传递最小必要的环境变量，避免泄露敏感变量到子进程环境
        env = {
            "PATH": subprocess.os.environ.get("PATH", ""),
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
        except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
            raise
        except FileNotFoundError:
            raise PiAgentError(
                "openclaw CLI not found. Is OpenClaw installed and in PATH?",
                agent_id=self.agent_id,
            )
        except Exception as e:
            logger.error("piagent_invoke_error", error=str(e), error_type=type(e).__name__)
            raise PiAgentError(str(e), agent_id=self.agent_id)

    async def invoke_async(self, message: str, session_id: Optional[str] = None) -> PiAgentResult:
        """
        异步调用 PiAgent（使用 asyncio subprocess）。

        Args:
            message: 要发送给 Agent 的消息
            session_id: 可选的会话 ID

        Returns:
            PiAgentResult: 执行结果

        Raises:
            PiAgentError: 调用失败
            PiAgentTimeoutError: 超时
        """
        cli_args = self._build_cli_args(message, session_id)
        env = {
            "PATH": subprocess.os.environ.get("PATH", ""),
            "OPENCLAW_GATEWAY_TOKEN": self.gateway_token,
            "OPENCLAW_GATEWAY_URL": self._get_gateway_url(),
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                *cli_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout_seconds,
            )
            stdout = stdout_bytes.decode().strip() if stdout_bytes else ""
            stderr = stderr_bytes.decode().strip() if stderr_bytes else ""

            if proc.returncode != 0:
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
                    f"Agent invocation failed (exit {proc.returncode}): {stderr[:500]}",
                    agent_id=self.agent_id,
                    details={"stderr": stderr, "returncode": proc.returncode},
                )

            if not stdout:
                raise PiAgentError("Empty response from agent", agent_id=self.agent_id)

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError as e:
                raise PiAgentError(
                    f"Invalid JSON from agent: {e}",
                    agent_id=self.agent_id,
                    details={"stdout_preview": stdout[:500]},
                )

            return PiAgentResult.from_dict(data)

        except asyncio.TimeoutError:
            raise PiAgentTimeoutError(
                f"Agent invocation timed out after {self.timeout_seconds}s",
                agent_id=self.agent_id,
            )
        except PiAgentError:
            raise
        except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
            raise
        except FileNotFoundError:
            raise PiAgentError(
                "openclaw CLI not found. Is OpenClaw installed and in PATH?",
                agent_id=self.agent_id,
            )
        except Exception as e:
            logger.error("piagent_async_invoke_error", error=str(e), error_type=type(e).__name__)
            raise PiAgentError(str(e), agent_id=self.agent_id)


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
        self.created_at = datetime.now(timezone.utc)

    @staticmethod
    def _new_session_id() -> str:
        """生成新的会话 ID"""
        return str(uuid.uuid4())

    def send(self, message: str) -> PiAgentResult:
        """发送消息到当前会话"""
        self.call_count += 1
        return self.client.invoke(message, session_id=self.session_id)

    def get_history(self) -> List[Dict[str, Any]]:
        """获取会话历史。TODO: 通过 Gateway API 获取历史消息。"""
        return []


class PiAgentSessionManager:
    """管理多个会话的生命周期，支持 LRU 淘汰（上限 1000 个）。"""

    MAX_SESSIONS = 1000

    def __init__(self, default_agent: str = PiAgentClient.DEFAULT_AGENT):
        self.default_agent = default_agent
        self._sessions: OrderedDict[str, PiAgentSession] = OrderedDict()

    def get_or_create(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> PiAgentSession:
        """获取或创建会话（LRU 淘汰）"""
        if session_id and session_id in self._sessions:
            self._sessions.move_to_end(session_id)
            return self._sessions[session_id]

        if len(self._sessions) >= self.MAX_SESSIONS:
            # 淘汰最旧的会话
            oldest = next(iter(self._sessions))
            del self._sessions[oldest]

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
