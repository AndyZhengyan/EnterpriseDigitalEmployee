"""Seed data — single source of truth for all initial dataset.

Imported by:
  - ops/main.py           (SEED_VERSIONS, SEED_CAPACITY for reset_seed_blueprints)
  - ops/db/_seed.py       (get_blueprints_data() in seed_all())
  - ops/db/_executions.py (DASHBOARD_STATS_BASELINE in _recalc_stats())

Both consumers must import from here; do not duplicate data elsewhere.
"""
from __future__ import annotations

from typing import Any

# ── Dashboard stats baseline ───────────────────────────────────────────────────
# These numbers represent the pre-existing token/task counts baked into
# dashboard_stats.  They are added to live execution totals in _recalc_stats().
DASHBOARD_STATS_BASELINE = {
    "total_token_usage": 19_480_000,
    "total_tasks": 4513,
    "success_count": 4242,
}

# ── Blueprint seed data ────────────────────────────────────────────────────────

SEED_CAPACITY: dict[str, dict[str, int]] = {
    "av-admin-001": {"used": 6, "max": 10},
    "av-legal-001": {"used": 1, "max": 5},
    "av-contract-001": {"used": 2, "max": 5},
    "av-swe-001": {"used": 5, "max": 10},
}

# SEED_VERSIONS is the format used by reset_seed_blueprints().
# It is also the basis for the full blueprints_data dict below.
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

# Blueprint identity metadata — matched to SEED_VERSIONS keys.
_BLUEPRINT_META = {
    "av-admin-001":    {"role": "行政专员",   "alias": "小白", "department": "综合管理部"},
    "av-legal-001":    {"role": "法务专员",   "alias": "明律", "department": "法务合规部"},
    "av-contract-001": {"role": "合同专员",   "alias": "墨言", "department": "商务运营部"},
    "av-swe-001":      {"role": "软件工程师", "alias": "码哥", "department": "技术研发部"},
}


def get_blueprints_data() -> list[dict[str, Any]]:
    """Return the full blueprints data list used by seed_data().

    Built deterministically from SEED_VERSIONS and _BLUEPRINT_META so
    all three structures stay in sync.
    """
    rows = []
    for bp_id, versions in SEED_VERSIONS.items():
        meta = _BLUEPRINT_META[bp_id]
        capacity = dict(SEED_CAPACITY[bp_id])
        rows.append({
            "id": bp_id,
            "role": meta["role"],
            "alias": meta["alias"],
            "department": meta["department"],
            "versions": versions,
            "capacity": capacity,
        })
    return rows
