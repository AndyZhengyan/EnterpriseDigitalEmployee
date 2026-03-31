"""PiAgent 同步调用冒烟测试

需要 PiAgent Gateway 运行在 ws://127.0.0.1:18789/。
本地手动验证用，CI 默认跳过。
"""

import pytest
from datetime import date

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
def test_piagent_sync_news_query():
    """同步调用 PiAgent 查询今日 AI 新闻"""
    client = PiAgentClient(agent_id="chat", thinking_level="medium")
    today = date.today().isoformat()
    query = f"Search for the top 3 most important AI news stories from today ({today}). Summarize them briefly."

    result = client.invoke(query)

    assert result.status == "ok"
    assert result.run_id is not None
    assert result.duration_ms > 0
    assert result.summary in ("completed", "success")
    assert result.text is not None
    assert len(result.text) > 0
