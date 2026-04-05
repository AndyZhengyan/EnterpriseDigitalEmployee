# tests/unit/apps/ops/test_execute_routes_to_blueprint.py
"""Tests: execute endpoint and demo scheduler route to blueprint_id, not hardcoded 'chat'."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def _init_test_db(tmp_path, monkeypatch):
    """Set up the temp DB with schema before TestClient triggers startup()."""
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("PIAGENT_CLI_STUB", "true")
    from apps.ops import db as db_module
    db_module.DB_PATH = str(tmp_path / "ops.db")
    from apps.ops.db import get_db, init_db
    init_db()
    conn = get_db()
    conn.close()


def test_execute_uses_blueprint_id_param(tmp_path, monkeypatch):
    """POST /api/ops/execute with blueprint_id routes _run_piagent to that agent_id."""
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app
    client = TestClient(app)

    with patch("apps.ops.main._run_piagent") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "runId": "stub-abc12345",
            "summary": "test stub",
            "result": {
                "meta": {
                    "agentMeta": {
                        "usage": {"input": 100, "output": 50, "cacheRead": 0},
                        "durationMs": 500,
                    }
                }
            },
        }
        resp = client.post("/api/ops/execute", json={
            "message": "test message",
            "blueprint_id": "av-admin-001",
        })
        assert resp.status_code == 200
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # Second positional arg is agent_id
        assert call_args[0][1] == "av-admin-001", (
            f"Expected agent_id='av-admin-001', got {call_args[0][1]!r}"
        )


def test_execute_defaults_to_none_when_no_blueprint_id(tmp_path, monkeypatch):
    """POST /api/ops/execute without blueprint_id passes None (letting openclaw pick)."""
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app
    client = TestClient(app)

    with patch("apps.ops.main._run_piagent") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "runId": "stub-abc12345",
            "summary": "test stub",
            "result": {
                "meta": {
                    "agentMeta": {
                        "usage": {"input": 100, "output": 50, "cacheRead": 0},
                        "durationMs": 500,
                    }
                }
            },
        }
        resp = client.post("/api/ops/execute", json={
            "message": "test message",
        })
        assert resp.status_code == 200
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # agent_id should be None (no blueprint_id in request)
        assert call_args[0][1] is None, (
            f"Expected agent_id=None, got {call_args[0][1]!r}"
        )


def test_demo_scheduler_uses_blueprint_id(tmp_path, monkeypatch):
    """The demo scheduler rotates through seeded blueprint IDs, not 'chat'."""
    import threading
    import time

    _init_test_db(tmp_path, monkeypatch)

    from apps.ops import main as ops_main

    # Track which agent_ids were passed to _run_piagent across all invocations
    captured_agent_ids = []

    def track_run(message, agent_id, timeout=60):
        captured_agent_ids.append(agent_id)
        # Return a valid stub so the scheduler loop can continue
        return {
            "status": "ok",
            "runId": f"stub-{len(captured_agent_ids):03d}",
            "summary": "tracked",
            "result": {
                "meta": {
                    "agentMeta": {
                        "usage": {"input": 100, "output": 50, "cacheRead": 0},
                        "durationMs": 500,
                    }
                }
            },
        }

    seeded_bp_ids = ["av-admin-001", "av-legal-001", "av-contract-001", "av-swe-001"]

    monkeypatch.setattr(ops_main, "_run_piagent", track_run)

    # Start the scheduler and let it run 3 iterations
    ops_main._runner_active = True
    t = threading.Thread(target=ops_main._demo_scheduler, daemon=True)
    t.start()
    # Wait until we have at least 3 captured calls
    for _ in range(50):
        if len(captured_agent_ids) >= 3:
            break
        time.sleep(0.1)
    ops_main._runner_active = False
    t.join(timeout=2)

    assert len(captured_agent_ids) >= 1, "Scheduler never called _run_piagent"
    for agent_id in captured_agent_ids[:3]:
        assert agent_id in seeded_bp_ids, (
            f"Expected one of {seeded_bp_ids}, got {agent_id!r}"
        )
        assert agent_id != "chat", (
            f"Scheduler should not use hardcoded 'chat', got {agent_id!r}"
        )
