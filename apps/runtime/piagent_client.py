"""PiAgent 客户端

实现与 OpenClaw Gateway 的通信，支持 WebSocket (优先) 和 CLI (回退) 两种模式。
符合 OpenClaw Gateway Protocol V3。
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

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
        auth_payload = {"token": self.gateway_token}
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
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": settings.openclaw.client_id,
                    "version": settings.openclaw.version,
                    "platform": settings.openclaw.platform,
                    "mode": settings.openclaw.client_mode,
                },
                "role": "operator",
                "scopes": settings.openclaw.default_scopes,
                "auth": auth_payload,
                "device": {
                    "id": self.identity.device_id,
                    "publicKey": self.identity.public_key,
                    "signature": signature,
                    "signedAt": ts_now,
                    "nonce": nonce,
                },
            },
        }
        await ws.send(json.dumps(connect_req))

        # 3. 校验握手结果
        hello = json.loads(await ws.recv())
        if not hello.get("ok"):
            await ws.close()
            raise PiAgentAuthError(f"Gateway rejected WebSocket: {hello.get('error')}")

        return ws

    async def ainvoke(self, message: str, session_id: Optional[str] = None) -> PiAgentResult:
        """异步调用入口"""
        log = logger.bind(agent_id=self.agent_id, session_id=session_id)

        try:
            async with await self._connect_and_handshake() as ws:
                invoke_id = f"inv-{uuid.uuid4().hex[:8]}"
                invoke_req = {
                    "type": "req",
                    "id": invoke_id,
                    "method": "chat.send",
                    "params": {
                        "sessionKey": f"agent:{self.agent_id}:{session_id or 'main'}",
                        "message": message,
                        "thinking": self.thinking_level,
                        "idempotencyKey": str(uuid.uuid4()),
                    },
                }
                await ws.send(json.dumps(invoke_req))

                final_payload = {}
                async for msg_raw in ws:
                    msg = json.loads(msg_raw)

                    if msg.get("type") == "res" and msg.get("id") == invoke_id:
                        if not msg.get("ok"):
                            raise PiAgentError(f"Execution failed: {msg.get('error')}")
                        payload = msg.get("payload", {})
                        final_payload = {
                            "runId": payload.get("runId", invoke_id),
                            "status": "ok",
                            "summary": payload.get("summary", ""),
                            "result": payload,
                        }
                        break

                if not final_payload:
                    raise PiAgentError("No response from Gateway")

                return PiAgentResult.from_dict(final_payload)

        except Exception as e:
            log.error("piagent_invoke_error", error=str(e))
            raise

    async def astream(self, message: str, session_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用入口"""
        try:
            ws = await self._connect_and_handshake()
            invoke_id = f"inv-{uuid.uuid4().hex[:8]}"
            invoke_req = {
                "type": "req",
                "id": invoke_id,
                "method": "chat.send",
                "params": {
                    "sessionKey": f"agent:{self.agent_id}:{session_id or 'main'}",
                    "message": message,
                    "thinking": self.thinking_level,
                    "idempotencyKey": str(uuid.uuid4()),
                },
            }
            await ws.send(json.dumps(invoke_req))

            async with ws:
                async for msg_raw in ws:
                    data = json.loads(msg_raw)

                    if data.get("type") == "event":
                        event = data.get("event")
                        payload = data.get("payload", {})
                        if event == "agent.chunk":
                            yield {
                                "type": "chunk",
                                "content": payload.get("content", ""),
                                "runId": payload.get("runId"),
                            }
                        elif event == "status":
                            yield {"type": "status_update", "message": payload.get("status") or ""}

                    elif data.get("type") == "res" and data.get("id") == invoke_id:
                        if data.get("ok"):
                            res_payload = data.get("payload", {})
                            yield {
                                "type": "agent_response",
                                "summary": res_payload.get("summary", ""),
                                "runId": res_payload.get("runId"),
                                "result": res_payload,
                            }
                        break
        except Exception:
            logger.exception("piagent_stream_error")
            raise

    def invoke(self, message: str, session_id: Optional[str] = None) -> PiAgentResult:
        """同步回退方案：CLI 调用"""
        cli_args = [
            "openclaw",
            "agent",
            "--agent",
            self.agent_id,
            "--message",
            message,
            "--json",
            "--thinking",
            self.thinking_level,
        ]
        if session_id:
            cli_args.extend(["--session-id", session_id])

        env = {
            **os.environ,
            "OPENCLAW_GATEWAY_TOKEN": self.gateway_token,
            "OPENCLAW_GATEWAY_URL": f"http://{settings.openclaw.gateway_host}:{settings.openclaw.gateway_port}",
        }

        try:
            res = subprocess.run(cli_args, capture_output=True, text=True, env=env, timeout=300)
            if res.returncode != 0:
                raise PiAgentError(f"CLI Error: {res.stderr}")
            return PiAgentResult.from_dict(json.loads(res.stdout))
        except Exception as e:
            raise PiAgentError(f"CLI invocation failed: {e}")
