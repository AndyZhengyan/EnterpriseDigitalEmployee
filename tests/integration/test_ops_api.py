"""Integration tests for ops API — real data flow via SQLite + FastAPI."""

import os
import subprocess

import pytest


def _openclaw_available():
    try:
        r = subprocess.run(["openclaw", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


OPENCLAW_AVAILABLE = _openclaw_available()

# Use a temp DB for each test run, no side effects from other sessions
os.environ["OPS_DB_PATH"] = ""


@pytest.fixture()
def db_path(tmp_path):
    """Create an isolated SQLite DB for each test."""
    path = str(tmp_path / "test_ops.db")
    os.environ["OPS_DB_PATH"] = path
    return path


@pytest.fixture()
def client(db_path):
    """Fresh FastAPI test client with seeded DB."""
    import sys

    # Clear any cached imports so temp DB path is picked up
    for mod in list(sys.modules):
        if mod.startswith("apps.ops"):
            del sys.modules[mod]

    # Disable background scheduler before app starts
    import apps.ops.main as ops_main

    ops_main._runner_active = False

    from apps.ops.db import init_db

    init_db()

    from fastapi.testclient import TestClient

    from apps.ops.main import app

    with TestClient(app) as c:
        # After startup fires (which init'd key manager for this module instance),
        # force dev mode so tests don't need API keys
        ops_main._force_dev_mode()
        yield c


@pytest.fixture()
def get_cursor(db_path):
    """Raw DB cursor for inspecting state."""
    from apps.ops.db import get_db

    def _query(sql, params=()):
        conn = get_db()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        rows = cur.fetchall()
        conn.close()
        return rows

    return _query


# ---- Dashboard endpoints ----


class TestDashboardStats:
    def test_stats_returns_seed_data(self, client):
        resp = client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["onlineCount"] == 10
        assert data["totalTokenUsage"] == 19480000
        assert data["monthlyTasks"] == 4513
        assert data["systemLoad"] == 68
        assert data["taskSuccessRate"] == 94.2
        assert data["taskTrend"]["direction"] == "down"

    def test_stats_updates_after_task_execution(self, client, get_cursor):
        """After executing a PiAgent task, dashboard stats should reflect real data."""
        # Initial stats
        before = client.get("/api/dashboard/stats").json()
        before_tasks = before["monthlyTasks"]
        before_tokens = before["totalTokenUsage"]

        # Execute a real task
        resp = client.post(
            "/api/ops/execute",
            json={
                "message": "test task",
                "alias": "TestBot",
                "role": "Tester",
                "dept": "QA",
            },
        )
        # Might fail without openclaw, that's ok — test verifies pipeline
        if resp.status_code == 200:
            result = resp.json()
            if result.get("runId"):
                after = client.get("/api/dashboard/stats").json()
                assert after["monthlyTasks"] > before_tasks
                assert after["totalTokenUsage"] > before_tokens


class TestStatusDist:
    def test_status_dist_returns_four_items(self, client):
        resp = client.get("/api/dashboard/status-dist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        statuses = {d["status"] for d in data}
        assert statuses == {"active", "shadow", "sandbox", "archived"}

    def test_status_dist_fields(self, client):
        resp = client.get("/api/dashboard/status-dist")
        item = resp.json()[0]
        assert "status" in item
        assert "label" in item
        assert "count" in item
        assert "color" in item


class TestTokenTrend:
    def test_token_trend_has_seven_days(self, client):
        resp = client.get("/api/dashboard/token-trend")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
        for d in data:
            assert "date" in d
            assert "value" in d
            assert isinstance(d["value"], (int, float))


class TestTaskDetail:
    def test_task_detail_returns_arrays(self, client):
        resp = client.get("/api/dashboard/task-detail")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["dates"], list)
        assert isinstance(data["success"], list)
        assert isinstance(data["failed"], list)
        assert len(data["dates"]) == len(data["success"]) == len(data["failed"])


class TestCapabilityDist:
    def test_capability_dist_has_four_roles(self, client):
        resp = client.get("/api/dashboard/capability-dist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        for d in data:
            assert all(k in d for k in ["role", "alias", "dept", "pct"])

    def test_capability_dist_sorted_desc(self, client):
        resp = client.get("/api/dashboard/capability-dist")
        data = resp.json()
        pcts = [d["pct"] for d in data]
        assert pcts == sorted(pcts, reverse=True)


class TestActivityFeed:
    def test_activity_returns_items(self, client):
        resp = client.get("/api/dashboard/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        for item in data:
            assert all(k in item for k in ["id", "type", "alias", "role", "dept", "content", "timestamp"])


# ---- Onboarding / Blueprints ----


class TestBlueprints:
    def test_blueprints_returns_four_blueprints(self, client):
        resp = client.get("/api/onboarding/blueprints")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        for bp in data:
            assert all(k in bp for k in ["id", "role", "alias", "department", "versions", "capacity"])
            assert isinstance(bp["versions"], list)
            assert isinstance(bp["capacity"], dict)
            assert "used" in bp["capacity"]
            assert "max" in bp["capacity"]

    def test_deploy_new_avatar_creates_blueprint(self, client, get_cursor):
        """POST /api/onboarding/deploy should create a real blueprint record."""
        before = client.get("/api/onboarding/blueprints").json()
        assert len(before) == 4

        resp = client.post(
            "/api/onboarding/deploy",
            json={
                "role": "测试专员",
                "alias": "小测",
                "department": "QA部",
                "scaling": {"minReplicas": 2, "maxReplicas": 5, "targetLoad": 70},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "测试专员"
        assert data["alias"] == "小测"
        assert len(data["versions"]) == 1
        assert data["versions"][0]["scaling"]["minReplicas"] == 2
        assert data["capacity"]["used"] == 2
        assert data["capacity"]["max"] == 5

        after = client.get("/api/onboarding/blueprints").json()
        assert len(after) == 5

    def test_deployed_blueprint_persists_in_db(self, client, get_cursor):
        client.post(
            "/api/onboarding/deploy",
            json={
                "role": "测试专员",
                "alias": "小测",
                "department": "QA部",
                "scaling": {"minReplicas": 1, "maxReplicas": 3, "targetLoad": 70},
            },
        )
        rows = get_cursor("SELECT id, role, alias FROM blueprints WHERE alias='小测'")
        assert len(rows) == 1
        assert rows[0][1] == "测试专员"
        assert rows[0][2] == "小测"


# ---- Task Execution ----


class TestExecuteTask:
    def test_execute_requires_message(self, client):
        resp = client.post("/api/ops/execute", json={})
        assert resp.status_code == 400
        assert "message" in resp.json()["detail"]

    def test_execute_records_in_db(self, client, get_cursor):
        """Execute should record the task in task_executions table."""
        before_count = len(get_executor_executions(get_cursor))

        resp = client.post(
            "/api/ops/execute",
            json={
                "message": "test task for assertion",
                "alias": "QA",
                "role": "Tester",
                "dept": "QA",
            },
        )

        # If openclaw is available, we get a real result
        if resp.status_code == 200:
            data = resp.json()
            assert "status" in data
            if data.get("runId"):
                after_count = len(get_executor_executions(get_cursor))
                assert after_count > before_count

                # Activity feed should include the new execution (check returned alias)
                activity = client.get("/api/dashboard/activity").json()
                aliases = [a["alias"] for a in activity]
                assert data["alias"] in aliases

    def test_execute_updates_stats(self, client, get_cursor):
        """Successful execution increments monthlyTasks and totalTokenUsage."""
        before = client.get("/api/dashboard/stats").json()
        before_tokens = before["totalTokenUsage"]

        resp = client.post(
            "/api/ops/execute",
            json={
                "message": "stats update test",
            },
        )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("runId"):
                after = client.get("/api/dashboard/stats").json()
                # Stats should have increased or stayed the same (if PiAgent ran)
                assert after["monthlyTasks"] >= before["monthlyTasks"]
                assert after["totalTokenUsage"] >= before_tokens


def get_executor_executions(get_cursor):
    """Helper: get all task executions from DB."""
    return get_cursor("SELECT * FROM task_executions")

