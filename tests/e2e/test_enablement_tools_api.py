"""E2E: Enablement Tools Registry API — CRUD lifecycle."""

import pytest
import os
import sys

# Use isolated temp DB per test
os.environ["OPS_DB_PATH"] = ""


@pytest.fixture(autouse=True)
def clear_ops_modules():
    """Force fresh module imports so temp DB path is picked up."""
    mods = [m for m in sys.modules if m.startswith("apps.ops")]
    for m in mods:
        del sys.modules[m]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_enablement.db")
    os.environ["OPS_DB_PATH"] = path
    return path


@pytest.fixture
def client(db_path):
    from apps.ops.db import init_db
    init_db()

    import apps.ops.main as ops_main
    ops_main._runner_active = False

    from fastapi.testclient import TestClient
    from apps.ops.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        ops_main._force_dev_mode()
        yield c


# ── Tools Registry ──────────────────────────────────────────────


class TestToolsList:
    def test_list_returns_20_builtin_tools(self, client):
        resp = client.get("/enablement/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 20

    def test_list_tools_have_required_fields(self, client):
        resp = client.get("/enablement/tools")
        for tool in resp.json():
            assert "id" in tool
            assert "name" in tool
            assert "description" in tool
            assert "created_at" in tool

    def test_builtin_tools_present(self, client):
        resp = client.get("/enablement/tools")
        names = {t["name"] for t in resp.json()}
        assert "web_search" in names
        assert "exec" in names
        assert "browser" in names
        assert "image" in names


class TestToolsCreate:
    def test_create_tool(self, client):
        resp = client.post(
            "/enablement/tools",
            json={"name": "my-custom-tool", "description": "A test tool"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-custom-tool"
        assert data["description"] == "A test tool"
        assert data["id"].startswith("custom-")

    def test_create_tool_requires_name(self, client):
        resp = client.post("/enablement/tools", json={"description": "No name"})
        assert resp.status_code == 400

    def test_create_tool_idempotent_name(self, client):
        """Same name twice — second should return 409 (UNIQUE constraint on name)."""
        client.post("/enablement/tools", json={"name": "dup-tool", "description": "First"})
        resp = client.post("/enablement/tools", json={"name": "dup-tool", "description": "Second"})
        assert resp.status_code == 409

    def test_created_tool_appears_in_list(self, client):
        client.post("/enablement/tools", json={"name": "listed-tool", "description": "Test"})
        resp = client.get("/enablement/tools")
        names = {t["name"] for t in resp.json()}
        assert "listed-tool" in names


class TestToolsUpdate:
    def test_update_tool_description(self, client):
        # Create
        create_resp = client.post(
            "/enablement/tools",
            json={"name": "update-test", "description": "Original"},
        )
        tool_id = create_resp.json()["id"]

        # Update
        resp = client.put(
            f"/enablement/tools/{tool_id}",
            json={"description": "Updated description"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put(
            "/enablement/tools/nonexistent-id",
            json={"description": "Updated"},
        )
        assert resp.status_code == 404


class TestToolsDelete:
    def test_delete_tool(self, client):
        # Create
        create_resp = client.post(
            "/enablement/tools",
            json={"name": "delete-me", "description": "Will be deleted"},
        )
        tool_id = create_resp.json()["id"]

        # Delete
        resp = client.delete(f"/enablement/tools/{tool_id}")
        assert resp.status_code == 200

        # Verify gone
        list_resp = client.get("/enablement/tools")
        ids = {t["id"] for t in list_resp.json()}
        assert tool_id not in ids

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/enablement/tools/no-such-id")
        assert resp.status_code == 404

    def test_delete_builtin_tool_works(self, client):
        """Builtin tools can be deleted (id == name for builtins)."""
        resp = client.delete("/enablement/tools/exec")
        # Builtin tools have id == name, so they CAN be deleted
        assert resp.status_code == 200
