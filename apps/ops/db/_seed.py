"""Seed data — dashboard stats, activity log, blueprints, and OpenClaw tools."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

OPENCLAW_BUILTIN_TOOLS = [
    ("exec", "运行 Shell 命令，管理后台进程"),
    ("code_execution", "沙箱远程 Python 分析"),
    ("browser", "控制 Chromium 浏览器"),
    ("web_search", "网络搜索"),
    ("web_fetch", "抓取网页内容"),
    ("read", "读取文件内容"),
    ("write", "写入文件内容"),
    ("edit", "编辑文件内容"),
    ("apply_patch", "多区块文件补丁"),
    ("message", "跨渠道发送消息"),
    ("canvas", "Node Canvas 控制"),
    ("nodes", "发现和定位配对设备"),
    ("cron", "定时任务管理"),
    ("gateway", "网关操作"),
    ("image", "图片分析/生成"),
    ("music_generate", "音乐生成"),
    ("video_generate", "视频生成"),
    ("tts", "文字转语音"),
    ("subagents", "子 Agent 管理"),
    ("session_status", "会话状态查询"),
]

_STATUS_ITEMS = [
    ("active", "正式上岗", 10, "#4A7C59"),
    ("shadow", "试用期", 4, "#C47A3D"),
    ("sandbox", "沙盒态", 2, "#9A9490"),
    ("archived", "退役", 2, "#A8A29E"),
]

_TOKEN_DATA = [
    ("03-27", 1.82),
    ("03-28", 2.34),
    ("03-29", 1.56),
    ("03-30", 0.98),
    ("03-31", 3.12),
    ("04-01", 2.78),
    ("04-02", 1.64),
]

_TASK_DATES = ["03-27", "03-28", "03-29", "03-30", "03-31", "04-01", "04-02"]
_TASK_SUCCESS = [138, 187, 106, 82, 221, 191, 111]
_TASK_FAILED = [7, 11, 6, 5, 13, 10, 7]

_CAP_ITEMS = [
    ("数据分析师", "小龙", "商业智能部", 73),
    ("内容创作员", "墨白", "市场部", 18),
    ("运维工程师", "铁柱", "基础设施部", 6),
    ("客服专员", "小红", "客服部", 3),
]

_ACTIVITIES = [
    (
        "act-001",
        "task_completed",
        "EMP-015",
        "小龙",
        "数据分析师",
        "商业智能部",
        "完成了「月度数据标注质量报告」",
        -180,
    ),
    ("act-002", "shadow_pass", "EMP-002", "小红", "客服专员", "客服部", "试用期产出比对通过", -1080),
    ("act-003", "employee_joined", None, "建国", "知识库管理员", "数智部", "新员工入职（沙盒态）", -3600),
    ("act-004", "task_failed", "EMP-005", "铁柱", "运维工程师", "基础设施部", "任务执行失败，请检查日志", -7200),
    ("act-005", "task_completed", "EMP-013", "雅婷", "产品经理", "产品部", "完成了「用户调研报告 v2.3」", -10800),
    ("act-006", "task_completed", "EMP-007", "浩宇", "算法工程师", "研发部", "完成了「推荐算法准确性验证」", -18000),
    ("act-007", "status_changed", "EMP-016", "静怡", "品牌设计师", "市场部", "状态变更为「试用期」", -28800),
    ("act-008", "task_completed", "EMP-012", "凯文", "前端工程师", "研发部", "完成了「前端组件库升级评估」", -43200),
]


def seed_all():
    """Insert all seed data if the database is still empty."""
    from ._schema import get_db

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM dashboard_stats")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # Dashboard stats — values derived from _seed_data.DASHBOARD_STATS_BASELINE
    from .._seed_data import DASHBOARD_STATS_BASELINE

    b = DASHBOARD_STATS_BASELINE
    dash_stats = (
        10,                                   # online_count
        b["total_token_usage"],               # 19_480_000
        b["total_tasks"],                     # 4513
        68,                                   # system_load
        94.2,                                 # task_success_rate
        3.2,                                  # token_efficiency
        -8.7,                                 # task_trend_change
        2.1,                                  # success_rate_change
    )
    cur.execute(
        """
        INSERT INTO dashboard_stats
            (online_count, total_token_usage, monthly_tasks, system_load,
             task_success_rate, token_efficiency, task_trend_change, success_rate_change)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        dash_stats,
    )

    # Status distribution
    cur.executemany(
        "INSERT INTO status_dist (status, label, count, color) VALUES (?, ?, ?, ?)",
        _STATUS_ITEMS,
    )

    # Token daily
    cur.executemany(
        "INSERT INTO token_daily (date, value) VALUES (?, ?)",
        _TOKEN_DATA,
    )

    # Task detail
    cur.execute(
        "INSERT INTO task_detail (dates, success, failed) VALUES (?, ?, ?)",
        (json.dumps(_TASK_DATES), json.dumps(_TASK_SUCCESS), json.dumps(_TASK_FAILED)),
    )

    # Capability distribution
    cur.executemany(
        "INSERT INTO capability_dist (role, alias, dept, pct) VALUES (?, ?, ?, ?)",
        _CAP_ITEMS,
    )

    # Activity log
    now = time.time()
    for act in _ACTIVITIES:
        ts = datetime.fromtimestamp(now + act[7], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur.execute(
            "INSERT INTO activity_log (id,type,employee_id,alias,role,dept,content,timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (act[0], act[1], act[2], act[3], act[4], act[5], act[6], ts),
        )

    # Blueprints
    from .._seed_data import get_blueprints_data

    for bp in get_blueprints_data():
        cur.execute(
            "INSERT INTO blueprints (id, role, alias, department, versions, capacity) VALUES (?, ?, ?, ?, ?, ?)",
            (
                bp["id"],
                bp["role"],
                bp["alias"],
                bp["department"],
                json.dumps(bp["versions"]),
                json.dumps(bp["capacity"]),
            ),
        )

    conn.commit()
    conn.close()


def seed_tools():
    """Seed OpenClaw built-in tools if the tools table is empty."""
    from ._schema import get_db

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tools")
    if cur.fetchone()[0] > 0:
        conn.close()
        return
    for name, description in OPENCLAW_BUILTIN_TOOLS:
        cur.execute(
            "INSERT OR IGNORE INTO tools (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (name, name, description, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )
    conn.commit()
    conn.close()
