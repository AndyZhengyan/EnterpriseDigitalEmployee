"""PiAgent WebSocket 异步调用冒烟测试

需要 PiAgent Gateway 运行在 ws://127.0.0.1:18789/。
本地手动验证用，CI 默认跳过。
"""

import pytest

from apps.runtime.piagent_client import PiAgentClient


def _is_piagent_available() -> bool:
    """检测 PiAgent Gateway 是否可用（通过尝试连接）。"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", 18789))
        sock.close()
        return True
    except OSError:
        return False


PIAGENT_MARK = pytest.mark.skipif(
    not _is_piagent_available(),
    reason="PiAgent Gateway not available on 127.0.0.1:18789",
)


@PIAGENT_MARK
@pytest.mark.asyncio
async def test_piagent_websocket_invoke_async():
    """WebSocket 异步完整调用 PiAgent（invoke_async）"""
    client = PiAgentClient(agent_id="chat", thinking_level="medium")
    query = "What time is it now? Answer briefly."

    result = await client.invoke_async(query)

    assert result.status == "ok"
    assert result.run_id is not None
    assert result.duration_ms > 0
    assert result.text is not None
