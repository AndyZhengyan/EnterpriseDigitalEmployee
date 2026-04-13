"""E2E: Avatar Config API — GET/PUT config, assembly into OpenClaw files."""

import os
import sys
from pathlib import Path

import pytest

os.environ["OPS_DB_PATH"] = ""


@pytest.fixture(autouse=True)
def clear_ops_modules():
    mods = [m for m in sys.modules if m.startswith("apps.ops")]
    for m in mods:
        del sys.modules[m]


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_avatar_config.db")
    os.environ["OPS_DB_PATH"] = path
    return path


@pytest.fixture
def openclaw_dir(tmp_path):
    d = tmp_path / ".openclaw"
    d.mkdir()
    os.environ["OPENCLAW_DIR"] = str(d)
    return d


@pytest.fixture
def client(db_path, openclaw_dir):
    from apps.ops.db import init_db
    init_db()

    import apps.ops.main as ops_main
    ops_main._runner_active = False

    from fastapi.testclient import TestClient
    from apps.ops.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        ops_main._force_dev_mode()
        yield c


# ── Deploy a blueprint first (precondition for config tests) ──


@pytest.fixture
def deployed_blueprint(client):
    resp = client.post(
        "/api/onboarding/deploy",
        json={
            "role": "测试专员",
            "alias": "配置测试员",
            "department": "研发部",
            "scaling": {"minReplicas": 1, "maxReplicas": 3, "targetLoad": 70},
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


# ── Avatar Config API ───────────────────────────────────────────


class TestAvatarConfigGet:
    def test_get_config_returns_fields(self, client, deployed_blueprint):
        resp = client.get(f"/onboarding/blueprints/{deployed_blueprint}/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "role" in data
        assert "alias" in data
        assert "department" in data
        assert "soul_content" in data
        assert "agents_content" in data
        assert "user_content" in data
        assert "tools_enabled" in data
        assert "selected_model" in data

    def test_get_config_not_found(self, client):
        resp = client.get("/onboarding/blueprints/nonexistent-bp/config")
        assert resp.status_code == 404


class TestAvatarConfigPut:
    def test_put_config_saves_to_db(self, client, deployed_blueprint):
        config = {
            "soul_content": "# SOUL.md\n\nTest soul content",
            "agents_content": "# AGENTS.md\n\nTest agents content",
            "user_content": "# USER.md\n\nTest user content",
            "tools_enabled": ["web_search", "exec"],
            "selected_model": "anthropic/claude-sonnet-4-6",
        }
        resp = client.put(
            f"/onboarding/blueprints/{deployed_blueprint}/config",
            json=config,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "saved"

        # Verify it persisted
        get_resp = client.get(f"/onboarding/blueprints/{deployed_blueprint}/config")
        data = get_resp.json()
        assert data["soul_content"] == "# SOUL.md\n\nTest soul content"
        assert data["agents_content"] == "# AGENTS.md\n\nTest agents content"
        assert data["user_content"] == "# USER.md\n\nTest user content"
        assert data["tools_enabled"] == ["web_search", "exec"]
        assert data["selected_model"] == "anthropic/claude-sonnet-4-6"

    def test_put_config_writes_openclaw_files(self, client, deployed_blueprint, openclaw_dir):
        """PUT should write SOUL.md / IDENTITY.md / AGENTS.md / USER.md / TOOLS.md to openclaw dir."""
        config = {
            "soul_content": "# Custom Soul\n\nI am a custom soul.",
            "agents_content": "# AGENTS\n\nCustom agents.",
            "user_content": "# USER\n\nCustom user.",
            "tools_enabled": ["web_search", "browser"],
            "selected_model": "openai/gpt-5.4",
        }
        resp = client.put(
            f"/onboarding/blueprints/{deployed_blueprint}/config",
            json=config,
        )
        assert resp.status_code == 200

        # Deploy already created the agent dir
        agent_dir = openclaw_dir / "agents" / deployed_blueprint / "agent"
        assert agent_dir.exists(), f"Agent dir not created: {agent_dir}"

        # Verify each file contains the custom content
        soul_file = agent_dir / "SOUL.md"
        assert soul_file.exists()
        assert "Custom Soul" in soul_file.read_text()

        agents_file = agent_dir / "AGENTS.md"
        assert agents_file.exists()
        assert "Custom agents" in agents_file.read_text()

        user_file = agent_dir / "USER.md"
        assert user_file.exists()
        assert "Custom user" in user_file.read_text()

        tools_file = agent_dir / "TOOLS.md"
        assert tools_file.exists()
        content = tools_file.read_text()
        assert "web_search" in content
        assert "browser" in content

        identity_file = agent_dir / "IDENTITY.md"
        assert identity_file.exists()

    def test_put_config_creates_backup(self, client, deployed_blueprint, openclaw_dir):
        """Writing files should create timestamped backups of existing files."""
        agent_dir = openclaw_dir / "agents" / deployed_blueprint / "agent"
        # Deploy already created SOUL.md — read its current content
        soul_file = agent_dir / "SOUL.md"
        assert soul_file.exists(), "SOUL.md should exist from deploy"
        original_content = soul_file.read_text()

        # Overwrite soul_content via PUT
        resp = client.put(
            f"/onboarding/blueprints/{deployed_blueprint}/config",
            json={"soul_content": "New content"},
        )
        assert resp.status_code == 200

        # There should be a backup file with the original content
        backups = list(agent_dir.glob("SOUL.md.backup.*"))
        assert len(backups) >= 1
        assert backups[0].read_text() == original_content

    def test_put_config_not_found_returns_404(self, client):
        resp = client.put(
            "/onboarding/blueprints/nonexistent/config",
            json={"soul_content": "test"},
        )
        assert resp.status_code == 404


class TestAvatarConfigPartialUpdate:
    def test_put_config_partial_update_preserves_other_fields(self, client, deployed_blueprint):
        # Set initial state with all fields
        client.put(
            f"/onboarding/blueprints/{deployed_blueprint}/config",
            json={
                "soul_content": "Initial soul",
                "agents_content": "Initial agents",
                "user_content": "Initial user",
                "tools_enabled": ["exec"],
                "selected_model": "anthropic/claude-opus-4-6",
            },
        )

        # Partial update — only soul_content
        client.put(
            f"/onboarding/blueprints/{deployed_blueprint}/config",
            json={"soul_content": "Updated soul"},
        )

        # Verify other fields preserved (not overwritten)
        get_resp = client.get(f"/onboarding/blueprints/{deployed_blueprint}/config")
        data = get_resp.json()
        assert data["soul_content"] == "Updated soul"
        assert data["agents_content"] == "Initial agents"
        assert data["user_content"] == "Initial user"
        assert data["tools_enabled"] == ["exec"]
        assert data["selected_model"] == "anthropic/claude-opus-4-6"
