# tests/unit/apps/ops/test_deploy_agent_sync.py
"""Integration tests: deploy/delete endpoints create/remove openclaw agent directories."""

from fastapi.testclient import TestClient


def _init_test_db(tmp_path, monkeypatch):
    """Set up the temp DB with schema before TestClient triggers startup()."""
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setattr("apps.ops.db.DB_PATH", str(tmp_path / "ops.db"))
    # Force DB_PATH recompute by reloading the module-level variable
    from apps.ops import db as db_module
    db_module.DB_PATH = str(tmp_path / "ops.db")
    from apps.ops.db import get_db, init_db
    init_db()
    conn = get_db()
    conn.close()


def test_deploy_creates_openclaw_agent(tmp_path, monkeypatch):
    """POST /api/onboarding/deploy creates openclaw agent directory."""
    # Setup temp directory with template agent
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    template = agents_dir / "template-agent" / "agent"
    template.mkdir(parents=True)
    (template / "auth-profiles.json").write_text("{}")
    (template / "models.json").write_text("{}")

    # Patch openclaw dir so registry writes to tmp
    monkeypatch.setenv("OPENCLAW_DIR", str(tmp_path))
    # Initialize temp DB before TestClient triggers startup()
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app
    client = TestClient(app)

    resp = client.post("/api/onboarding/deploy", json={
        "role": "客服专员",
        "alias": "小美",
        "department": "客服部",
        "scaling": {"minReplicas": 1, "maxReplicas": 3, "targetLoad": 60},
        "soul": {"description": "热情友好", "communication_style": "亲切简洁"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"].startswith("av-")

    agent_dir = tmp_path / "agents" / data["id"] / "agent"
    assert agent_dir.exists()
    assert (agent_dir / "SOUL.md").exists()
    soul_content = (agent_dir / "SOUL.md").read_text()
    assert "小美" in soul_content
    assert "客服专员" in soul_content
    assert "热情友好" in soul_content


def test_delete_removes_openclaw_agent(tmp_path, monkeypatch):
    """DELETE /api/onboarding/blueprints/{id} removes the agent directory."""
    # Setup temp directory with template agent
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    template = agents_dir / "template-agent" / "agent"
    template.mkdir(parents=True)
    (template / "auth-profiles.json").write_text("{}")
    (template / "models.json").write_text("{}")

    monkeypatch.setenv("OPENCLAW_DIR", str(tmp_path))
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app
    client = TestClient(app)

    # Deploy first
    resp = client.post("/api/onboarding/deploy", json={
        "role": "测试",
        "alias": "Tester",
        "department": "测试部",
        "scaling": {"minReplicas": 1, "maxReplicas": 3, "targetLoad": 60},
        "soul": {"description": "test", "communication_style": "test"},
    })
    assert resp.status_code == 200
    bp_id = resp.json()["id"]
    agent_dir = tmp_path / "agents" / bp_id
    assert agent_dir.exists()

    # Delete and verify directory is removed
    resp = client.delete(f"/api/onboarding/blueprints/{bp_id}")
    assert resp.status_code == 200
    assert not agent_dir.exists()


def test_deploy_soul_md_includes_department(tmp_path, monkeypatch):
    """POST /api/onboarding/deploy writes department into SOUL.md."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    template = agents_dir / "template-agent" / "agent"
    template.mkdir(parents=True)
    (template / "auth-profiles.json").write_text("{}")
    (template / "models.json").write_text("{}")

    monkeypatch.setenv("OPENCLAW_DIR", str(tmp_path))
    _init_test_db(tmp_path, monkeypatch)

    from apps.ops.main import app
    client = TestClient(app)

    resp = client.post("/api/onboarding/deploy", json={
        "role": "数据分析师",
        "alias": "小龙",
        "department": "商业智能部",
        "scaling": {"minReplicas": 1, "maxReplicas": 5, "targetLoad": 60},
        "soul": {"description": "精准分析", "communication_style": "数据驱动"},
    })
    assert resp.status_code == 200
    bp_id = resp.json()["id"]

    soul_content = (tmp_path / "agents" / bp_id / "agent" / "SOUL.md").read_text()
    assert "商业智能部" in soul_content
    assert "精准分析" in soul_content
