"""Integration tests for Oracle knowledge archive API — /api/oracle/archives."""

import os
import sys
from urllib.parse import quote

import pytest

# Ensure a clean module state before importing ops
os.environ["OPS_DB_PATH"] = ":memory:"


@pytest.fixture()
def db_path(tmp_path):
    path = str(tmp_path / "test_oracle.db")
    os.environ["OPS_DB_PATH"] = path
    return path


@pytest.fixture()
def oracle_dir(tmp_path):
    """Create a temporary oracle directory structure."""
    d = tmp_path / "oracle"
    (d / "avatar").mkdir(parents=True)
    (d / "import").mkdir(parents=True)
    os.environ["ORACLE_DIR"] = str(d)
    return d


@pytest.fixture()
def client(db_path, oracle_dir):
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
def seeded_archives(oracle_dir):
    """Write sample .md archive files into the oracle directory."""

    def _md(title, source, contributor, created_at, tags):
        return (
            f"---\n"
            f"title: {title}\n"
            f"source: {source}\n"
            f"contributor: {contributor}\n"
            f"created_at: {created_at}\n"
            f"tags: {tags}\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"正文内容...\n"
        )

    files = [
        (
            oracle_dir / "avatar" / "合同风险识别.md",
            _md("合同风险识别", "avatar", "明律", "2026-04-07", "[合同, 法务]"),
        ),
        (
            oracle_dir / "avatar" / "供应商管理.md",
            _md("供应商管理", "avatar", "小白", "2026-04-06", "[供应商, 采购]"),
        ),
        (
            oracle_dir / "import" / "采购流程规范.md",
            _md("采购流程规范", "import", "管理员", "2026-04-05", "[采购, 流程]"),
        ),
    ]
    for fp, content in files:
        fp.write_text(content, encoding="utf-8")
    return files


class TestListArchives:
    def test_list_archives_returns_all(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_archives_filter_by_source(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives?source=avatar")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["source"] == "avatar"

    def test_list_archives_filter_by_import_source(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives?source=import")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["source"] == "import"

    def test_list_archives_response_fields(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives?source=avatar")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "id" in item
        assert "title" in item
        assert "source" in item
        assert "contributor" in item
        assert "createdAt" in item
        assert "tags" in item
        assert "path" in item

    def test_list_archives_empty_for_unknown_source(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives?source=unknown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestGetArchive:
    def test_get_archive_by_id(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives/合同风险识别")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["id"] == "合同风险识别"
        assert data["meta"]["title"] == "合同风险识别"
        assert data["meta"]["source"] == "avatar"
        assert data["meta"]["contributor"] == "明律"
        assert data["meta"]["tags"] == ["合同", "法务"]
        assert "正文内容" in data["content"]

    def test_get_archive_404(self, client, seeded_archives):
        resp = client.get("/api/oracle/archives/不存在的档案")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Archive not found"

    def test_get_archive_url_decoded(self, client, seeded_archives):
        """URL-encoded slugs should be decoded correctly."""
        resp = client.get("/api/oracle/archives/%E5%90%88%E5%90%8C%E9%A3%8E%E9%99%A9%E8%AF%86%E5%88%AB")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["id"] == "合同风险识别"


class TestUploadArchive:
    def test_upload_archive(self, client, seeded_archives, oracle_dir):
        resp = client.post(
            "/api/oracle/archives/upload",
            json={
                "title": "测试上传",
                "source": "import",
                "content": "# 测试上传\n\n这是一段测试内容。",
                "contributor": "测试员",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "path" in data
        assert data["message"] == "上传成功"
        assert data["path"].startswith("import/")

        # Verify file was created
        slug = data["id"]
        fp = oracle_dir / "import" / f"{slug}.md"
        assert fp.exists()
        content = fp.read_text(encoding="utf-8")
        assert "测试上传" in content

    def test_upload_archive_title_required(self, client, seeded_archives):
        resp = client.post(
            "/api/oracle/archives/upload",
            json={"source": "import", "content": "正文"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "title is required"

    def test_upload_archive_invalid_source(self, client, seeded_archives):
        resp = client.post(
            "/api/oracle/archives/upload",
            json={"title": "测试", "source": "invalid", "content": "正文"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "source must be 'avatar' or 'import'"

    def test_upload_yaml_injection_blocked(self, client, seeded_archives):
        """Title containing YAML injection payload should be safely stored as title value."""
        resp = client.post(
            "/api/oracle/archives/upload",
            json={
                "title": "Test\n---\ninjected: evil",
                "source": "import",
                "content": "normal body",
                "contributor": "admin",
            },
        )
        assert resp.status_code == 200
        archive_id = resp.json()["id"]
        detail = client.get(f"/api/oracle/archives/{quote(archive_id, safe='')}")
        assert detail.status_code == 200
        # The title should be stored as-is, not parsed as having injected YAML keys
        assert detail.json()["meta"]["title"] == "Test\n---\ninjected: evil"

    def test_upload_archive_conflict(self, client, seeded_archives):
        """Uploading an archive with the same title should return 409."""
        resp = client.post(
            "/api/oracle/archives/upload",
            json={
                "title": "合同风险识别",
                "source": "avatar",
                "content": "duplicate body",
                "contributor": "admin",
            },
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_upload_archive_default_source(self, client, seeded_archives, oracle_dir):
        resp = client.post(
            "/api/oracle/archives/upload",
            json={"title": "无来源测试", "content": "正文内容"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["path"].startswith("import/")
