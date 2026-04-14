# tests/unit/apps/ops/test_execute_routes_to_blueprint.py
"""Tests: execute endpoint routes to blueprint_id."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def _init_test_db(tmp_path, monkeypatch):
    """Set up the temp DB with schema and key manager before TestClient triggers startup()."""
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("PIAGENT_CLI_STUB", "true")
    from apps.ops import db as db_module

    db_module.DB_PATH = str(tmp_path / "ops.db")
    from apps.ops.db import get_db, init_db

    init_db()
    conn = get_db()
    conn.close()

    # Initialize key manager so endpoints don't raise "Key manager not initialized"
    from apps.ops._auth import _force_dev_mode, _init_key_manager

    _init_key_manager(str(tmp_path / "ops.db"))
    # Force dev mode so tests don't need API keys
    _force_dev_mode()


def test_execute_uses_blueprint_id_param(tmp_path, monkeypatch):
    """POST /api/ops/execute with blueprint_id routes _run_piagent to that agent_id."""
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app

    client = TestClient(app)

    with patch("apps.ops.routers.execute._run_piagent") as mock_run:
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
        resp = client.post(
            "/api/ops/execute",
            json={
                "message": "test message",
                "blueprint_id": "av-admin-001",
            },
        )
        assert resp.status_code == 200
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # Second positional arg is agent_id
        assert call_args[0][1] == "av-admin-001", f"Expected agent_id='av-admin-001', got {call_args[0][1]!r}"


def test_execute_defaults_to_av_swe_when_no_blueprint_id(tmp_path, monkeypatch):
    """POST /api/ops/execute without blueprint_id defaults to av-swe-001."""
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app

    client = TestClient(app)

    with patch("apps.ops.routers.execute._run_piagent") as mock_run:
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
        resp = client.post(
            "/api/ops/execute",
            json={
                "message": "test message",
            },
        )
        assert resp.status_code == 200
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # agent_id defaults to "av-swe-001" when no blueprint_id in request
        assert call_args[0][1] == "av-swe-001", f"Expected agent_id='av-swe-001', got {call_args[0][1]!r}"
