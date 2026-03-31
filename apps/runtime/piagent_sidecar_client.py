"""PiAgent Sidecar Client

Communicates with the Node.js pi-mono sidecar via Unix Domain Socket + JSONL.
Zero侵入 pi-mono 源码 —— sidecar 进程由本模块管理。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import structlog

logger = structlog.get_logger("runtime.sidecar")


# ============== 错误定义 ==============


class PiAgentError(Exception):
    """PiAgent 调用错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


# ============== 数据结构 ==============


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]
    result: Optional[str] = None


@dataclass
class PiAgentSidecarResult:
    answer: str
    session_id: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    total_tokens: int = 0
    cost: float = 0.0
    duration_ms: int = 0


@dataclass
class PiAgentSidecarEvent:
    type: str
    data: Dict[str, Any]


# ============== Socket 辅助 ==============


async def _read_jsonl(reader: asyncio.StreamReader) -> Dict[str, Any]:
    line = await reader.readline()
    if not line:
        raise EOFError("Socket closed by sidecar")
    return json.loads(line.decode())


async def _write_jsonl(writer: asyncio.StreamWriter, msg: Dict[str, Any]) -> None:
    data = json.dumps(msg).encode() + b"\n"
    writer.write(data)
    await writer.drain()


# ============== PiAgentSidecarClient ==============


class PiAgentSidecarClient:
    DEFAULT_SOCKET = Path("/tmp/piagent.sock")
    DEFAULT_STARTUP_TIMEOUT = 10.0
    DEFAULT_REQUEST_TIMEOUT = 300.0

    def __init__(
        self,
        socket_path: Optional[Path] = None,
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        sidecar_script: Optional[Path] = None,
    ):
        self.socket_path: Path = socket_path or self.DEFAULT_SOCKET
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.sidecar_script: Optional[Path] = sidecar_script
        self._proc: Optional[asyncio.subprocess.Process] = None

    async def start(self) -> None:
        """Spawn sidecar 进程，建立 socket 连接"""
        if self._proc is not None:
            return
        script = self.sidecar_script or self._find_sidecar_script()
        env = {**asyncio.subprocess._MS_PIPE_ENV, "PIAGENT_SOCKET_PATH": str(self.socket_path)}
        self._proc = await asyncio.create_subprocess_exec(
            "npx", "tsx", str(script),
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        # 等待 socket 文件出现
        for _ in range(50):
            if self.socket_path.exists():
                break
            await asyncio.sleep(0.2)
        else:
            raise PiAgentError(f"Sidecar socket not created within {self.startup_timeout}s")
        await asyncio.wait_for(self._ping(), timeout=self.startup_timeout)
        logger.info("sidecar_started", socket=str(self.socket_path))

    async def _ping(self) -> None:
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        await _write_jsonl(writer, {"type": "ping"})
        resp = await _read_jsonl(reader)
        writer.close()
        await writer.wait_closed()
        if resp.get("type") != "pong":
            raise PiAgentError(f"Unexpected pong response: {resp}")

    async def stop(self) -> None:
        """优雅关闭 sidecar"""
        if self._proc is None:
            return
        try:
            reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
            await _write_jsonl(writer, {"type": "shutdown"})
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        self._proc.terminate()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._proc.kill()
        self._proc = None
        logger.info("sidecar_stopped")

    async def invoke(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> PiAgentSidecarResult:
        """发送 invoke 请求，等待 result"""
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        request_id = str(uuid.uuid4())
        await _write_jsonl(writer, {
            "type": "invoke",
            "id": request_id,
            "session_id": session_id,
            "message": message,
        })
        try:
            while True:
                resp = await asyncio.wait_for(_read_jsonl(reader), timeout=self.request_timeout)
                if resp.get("request_id") != request_id:
                    continue
                if resp["type"] == "result":
                    result = resp["result"]
                    return PiAgentSidecarResult(
                        answer=result.get("answer", ""),
                        session_id=result.get("session_id", ""),
                        tool_calls=[
                            ToolCall(name=tc["name"], args=tc["args"], result=None)
                            for tc in result.get("tool_calls", [])
                        ],
                        total_tokens=result.get("total_tokens", 0),
                        cost=float(result.get("cost", 0)),
                        duration_ms=result.get("duration_ms", 0),
                    )
                elif resp["type"] == "error":
                    raise PiAgentError(resp.get("detail", resp.get("error", "Unknown error")))
        finally:
            writer.close()
            await writer.wait_closed()

    async def invoke_streaming(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[PiAgentSidecarEvent]:
        """事件流订阅"""
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        request_id = str(uuid.uuid4())
        await _write_jsonl(writer, {
            "type": "invoke",
            "id": request_id,
            "session_id": session_id,
            "message": message,
        })
        try:
            while True:
                resp = await asyncio.wait_for(_read_jsonl(reader), timeout=self.request_timeout)
                if resp.get("request_id") != request_id:
                    continue
                yield PiAgentSidecarEvent(type=resp["type"], data=resp)
                if resp["type"] in ("result", "error"):
                    break
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    def _find_sidecar_script() -> Path:
        """从 apps.runtime 包路径推断 sidecar 入口"""
        import apps.runtime
        runtime_root = Path(apps.runtime.__file__).parent
        return runtime_root / "sidecar" / "src" / "index.ts"
