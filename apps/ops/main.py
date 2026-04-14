# apps/ops/main.py — AvatarOS Ops API (thin FastAPI router)
import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.tracing import get_logger as _ops_get_logger

from ._auth import (
    _force_dev_mode,
    _init_key_manager,
    get_key_manager,
    verify_api_key,
)
from ._piagent import _run_piagent
from .db import init_db

# Re-export for backward compatibility (tests and other modules import from here)
__all__ = [
    "get_key_manager",
    "verify_api_key",
    "_force_dev_mode",
    "_run_piagent",
]

CORS_ORIGINS = os.environ.get("OPS_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
_log = _ops_get_logger("ops")


# ── Lifespan ────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("OPS_DB_PATH", "data/ops.db")
    _init_key_manager(db_path)
    init_db()
    yield


# ── App ────────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="AvatarOS Ops API",
    description="AvatarOS 运营数据 + 入职中心 API + PiAgent 集成",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Test compatibility ────────────────────────────────────────────────────────
# Kept as a module-level attribute for backward compat with existing test fixtures
_runner_active = False


# ── Mount sub-routers (imported lazily to avoid circular import) ───────────────


def _mount_routers():
    from .routers import (
        admin,
        avatar,
        dashboard,
        execute,
        journal,
        onboarding,
        oracle,
        tools_registry,
    )

    app.include_router(admin.router)
    app.include_router(dashboard.router)
    app.include_router(execute.router)
    app.include_router(onboarding.router)
    app.include_router(avatar.router)
    app.include_router(tools_registry.router)
    app.include_router(journal.router)
    app.include_router(oracle.router)


_mount_routers()


# ── Seed data ─────────────────────────────────────────────────────────────────


SEED_VERSIONS: dict[str, list[dict[str, Any]]] = {
    "av-admin-001": [
        {
            "version": "v1.0.0",
            "status": "published",
            "traffic": 60,
            "replicas": 3,
            "config": {
                "soul": {"mbti": "ISFJ", "style": "简洁汇报", "priority": "效率优先"},
                "skills": ["飞书通知", "文档处理"],
                "tools": ["飞书API", "文档处理器"],
                "model": "claude-sonnet-4-7",
            },
            "scaling": {"min_replicas": 1, "max_replicas": 5, "target_load": 60},
        },
        {
            "version": "v1.0.1",
            "status": "published",
            "traffic": 40,
            "replicas": 2,
            "config": {
                "soul": {"mbti": "ISFJ", "style": "简洁汇报", "priority": "效率优先"},
                "skills": ["飞书通知", "文档处理", "数据录入"],
                "tools": ["飞书API", "文档处理器", "数据库连接器"],
                "model": "claude-sonnet-4-7",
            },
            "scaling": {"min_replicas": 1, "max_replicas": 5, "target_load": 60},
        },
        {
            "version": "v1.1.0-beta",
            "status": "testing",
            "traffic": 0,
            "replicas": 1,
            "config": {
                "soul": {"mbti": "INTJ", "style": "详细说明", "priority": "合规优先"},
                "skills": ["飞书通知", "文档处理", "数据分析", "合规检查"],
                "tools": ["飞书API", "文档处理器", "数据分析引擎"],
                "model": "claude-opus-4-7",
            },
            "scaling": {"min_replicas": 1, "max_replicas": 3, "target_load": 70},
        },
    ],
    "av-legal-001": [
        {
            "version": "v1.0.0",
            "status": "published",
            "traffic": 100,
            "replicas": 1,
            "config": {
                "soul": {"mbti": "INTJ", "style": "详细说明", "priority": "合规优先"},
                "skills": ["合同审核", "法规检索", "合规检查"],
                "tools": ["飞书API", "知识库检索", "合规引擎"],
                "model": "claude-opus-4-7",
            },
            "scaling": {"min_replicas": 1, "max_replicas": 3, "target_load": 60},
        },
    ],
    "av-contract-001": [
        {
            "version": "v1.0.0",
            "status": "published",
            "traffic": 100,
            "replicas": 2,
            "config": {
                "soul": {"mbti": "ESTJ", "style": "简洁汇报", "priority": "合规优先"},
                "skills": ["合同起草", "版本管理", "文档归档"],
                "tools": ["飞书API", "文档处理器", "版本追踪器"],
                "model": "claude-sonnet-4-7",
            },
            "scaling": {"min_replicas": 1, "max_replicas": 5, "target_load": 65},
        },
    ],
    "av-swe-001": [
        {
            "version": "v1.0.0",
            "status": "published",
            "traffic": 100,
            "replicas": 5,
            "config": {
                "soul": {"mbti": "INTP", "style": "详细说明", "priority": "效率优先"},
                "skills": ["代码开发", "代码审查", "技术写作"],
                "tools": ["git CLI", "GitHub MCP", "代码分析器"],
                "model": "claude-sonnet-4-7",
            },
            "scaling": {"min_replicas": 2, "max_replicas": 10, "target_load": 60},
        },
    ],
}

SEED_CAPACITY = {
    "av-admin-001": {"used": 6, "max": 10},
    "av-legal-001": {"used": 1, "max": 5},
    "av-contract-001": {"used": 2, "max": 5},
    "av-swe-001": {"used": 5, "max": 10},
}


@app.post("/api/test/reset-seeds", tags=["test"])
def reset_seed_blueprints(_: bool = Depends(verify_api_key)):
    """Reset all seed blueprints to their original versions and traffic.
    Used by E2E tests to ensure consistent state before each test."""
    from .db import get_db

    conn = get_db()
    cur = conn.cursor()
    for bp_id, versions in SEED_VERSIONS.items():
        total_used = sum(v["replicas"] for v in versions if v["traffic"] > 0)
        capacity = dict(SEED_CAPACITY[bp_id])
        capacity["used"] = total_used
        cur.execute(
            "UPDATE blueprints SET versions = ?, capacity = ? WHERE id = ?",
            (json.dumps(versions), json.dumps(capacity), bp_id),
        )
    conn.commit()
    conn.close()
    return {"reset": "ok", "seeds": list(SEED_VERSIONS.keys())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
