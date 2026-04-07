"""Integration tests for Journal audit log API — /api/journal/executions."""

import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

os.environ["OPS_DB_PATH"] = ""


@pytest.fixture()
def db_path(tmp_path):
    path = str(tmp_path / "test_journal.db")
    os.environ["OPS_DB_PATH"] = path
    return path


@pytest.fixture()
def client(db_path):
    # Clear cached ops modules so temp DB path is picked up
    for mod in list(sys.modules):
        if mod.startswith("apps.ops"):
            del sys.modules[mod]

    import apps.ops.main as ops_main

    ops_main._runner_active = False

    from apps.ops.db import init_db

    init_db()

    from fastapi.testclient import TestClient

    from apps.ops.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_executions(db_path):
    """Insert test task executions directly into the DB."""
    from apps.ops.db import get_db

    conn = get_db()
    cur = conn.cursor()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    yesterday = "2026-04-05T10:00:00Z"
    two_days_ago = "2026-04-04T08:00:00Z"

    rows = [
        (
            "exec-test-001",
            "run-001",
            "av-swe-001",
            "码哥",
            "软件工程师",
            "技术研发部",
            "实现用户登录功能",
            "ok",
            1000,
            200,
            500,
            1500,
            "完成了登录模块开发",
            now,
        ),
        (
            "exec-test-002",
            "run-002",
            "av-legal-001",
            "明律",
            "法务专员",
            "法务合规部",
            "审核采购合同",
            "ok",
            800,
            150,
            400,
            900,
            "合同审核完成",
            yesterday,
        ),
        (
            "exec-test-003",
            "run-003",
            "av-admin-001",
            "小白",
            "行政专员",
            "综合管理部",
            "处理费用报销申请",
            "error",
            300,
            50,
            100,
            300,
            "报销系统连接失败",
            two_days_ago,
        ),
        (
            "exec-test-004",
            "run-004",
            "av-swe-001",
            "码哥",
            "软件工程师",
            "技术研发部",
            "修复支付接口bug",
            "ok",
            1200,
            300,
            600,
            2000,
            "已修复并上线",
            yesterday,
        ),
    ]

    for r in rows:
        cur.execute(
            """INSERT INTO task_executions
               (id,run_id,blueprint_id,alias,role,dept,message,status,
                token_input,token_analysis,token_completion,duration_ms,summary,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            r,
        )
    conn.commit()
    conn.close()
    return rows


class TestExecutionsList:
    def test_executions_list_returns_all(self, client, seeded_executions):
        resp = client.get("/api/journal/executions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4

    def test_executions_filter_by_role(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?roles=软件工程师")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["role"] == "软件工程师"

    def test_executions_filter_by_multiple_roles(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?roles=软件工程师,法务专员")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        roles = {item["role"] for item in data["items"]}
        assert roles == {"软件工程师", "法务专员"}

    def test_executions_filter_by_dept(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?depts=技术研发部")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["dept"] == "技术研发部"

    def test_executions_filter_by_status(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?status=ok")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["status"] == "ok"

    def test_executions_filter_by_keyword(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?q=登录")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "登录" in data["items"][0]["message"]

    def test_executions_filter_by_date_range(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?start_date=2026-04-04&end_date=2026-04-06")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3  # exec-002, exec-003, exec-004

    def test_executions_pagination_limit(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert len(data["items"]) == 2

    def test_executions_pagination_offset(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?limit=2&offset=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert len(data["items"]) == 2

    def test_executions_combined_filters(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?roles=软件工程师&status=ok")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["role"] == "软件工程师"
            assert item["status"] == "ok"

    def test_executions_empty_result(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?roles=不存在的角色")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_executions_response_fields(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?limit=1")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "id" in item
        assert "runId" in item
        assert "blueprintId" in item
        assert "alias" in item
        assert "role" in item
        assert "dept" in item
        assert "message" in item
        assert "status" in item
        assert "tokenInput" in item
        assert "tokenCompletion" in item
        assert "tokenAnalysis" in item
        assert "tokenTotal" in item
        assert "durationMs" in item
        assert "summary" in item
        assert "createdAt" in item

    def test_executions_token_total_calculation(self, client, seeded_executions):
        resp = client.get("/api/journal/executions?limit=1")
        item = resp.json()["items"][0]
        expected_total = (item["tokenInput"] or 0) + (item["tokenCompletion"] or 0) + (item["tokenAnalysis"] or 0)
        assert item["tokenTotal"] == expected_total


class TestExecutionDetail:
    def test_execution_detail(self, client, seeded_executions):
        resp = client.get("/api/journal/executions/exec-test-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "exec-test-001"
        assert data["alias"] == "码哥"
        assert data["role"] == "软件工程师"
        assert data["status"] == "ok"

    def test_execution_detail_404(self, client, seeded_executions):
        resp = client.get("/api/journal/executions/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Execution not found"

    def test_execution_detail_fields(self, client, seeded_executions):
        resp = client.get("/api/journal/executions/exec-test-002")
        assert resp.status_code == 200
        data = resp.json()
        # Should NOT be wrapped in {total, items}
        assert "total" not in data
        assert "items" not in data
        # Should have all flat fields
        assert data["id"] == "exec-test-002"
        assert data["runId"] == "run-002"
        assert data["blueprintId"] == "av-legal-001"
        assert data["alias"] == "明律"
        assert data["role"] == "法务专员"
        assert data["dept"] == "法务合规部"
        assert data["message"] == "审核采购合同"
        assert data["status"] == "ok"
        assert data["tokenInput"] == 800
        assert data["tokenCompletion"] == 400
        assert data["tokenAnalysis"] == 150
        assert data["tokenTotal"] == 1350
        assert data["durationMs"] == 900
        assert data["summary"] == "合同审核完成"
