from pathlib import Path

from apps.runtime.piagent_sidecar_client import (
    PiAgentSidecarClient,
    PiAgentSidecarEvent,
    PiAgentSidecarResult,
    ToolCall,
)


def test_result_defaults():
    result = PiAgentSidecarResult(answer="test", session_id="s1")
    assert result.answer == "test"
    assert result.session_id == "s1"
    assert result.tool_calls == []
    assert result.total_tokens == 0
    assert result.cost == 0.0


def test_result_from_dict():
    data = {
        "answer": "42",
        "session_id": "sess-1",
        "tool_calls": [{"name": "read", "args": {"path": "a.txt"}}],
        "total_tokens": 100,
        "cost": 0.001,
        "duration_ms": 500,
    }
    result = PiAgentSidecarResult(**data)
    assert result.answer == "42"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "read"
    assert result.tool_calls[0].args == {"path": "a.txt"}
    assert result.tool_calls[0].result is None


def test_event_deserialization():
    event = PiAgentSidecarEvent(type="message_update", data={"delta": "hello"})
    assert event.type == "message_update"
    assert event.data["delta"] == "hello"


def test_client_default_socket():
    c = PiAgentSidecarClient()
    assert c.socket_path == Path("/tmp/piagent.sock")
    assert c.startup_timeout == 10.0
    assert c.request_timeout == 300.0


def test_client_custom_config(tmp_path):
    c = PiAgentSidecarClient(
        socket_path=tmp_path / "custom.sock",
        startup_timeout=5.0,
        request_timeout=60.0,
    )
    assert c.socket_path == tmp_path / "custom.sock"
    assert c.startup_timeout == 5.0
    assert c.request_timeout == 60.0


def test_tool_call_dataclass():
    tc = ToolCall(name="bash", args={"cmd": "ls"}, result="file1\nfile2")
    assert tc.name == "bash"
    assert tc.args == {"cmd": "ls"}
    assert tc.result == "file1\nfile2"


def test_piagent_error_details():
    from apps.runtime.piagent_sidecar_client import PiAgentError

    err = PiAgentError("something went wrong", details={"code": 500})
    assert str(err) == "something went wrong"
    assert err.details == {"code": 500}
