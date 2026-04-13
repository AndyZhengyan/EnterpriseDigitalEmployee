# apps/ops/db.py — SQLite database setup and seed data
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.environ.get("OPS_DB_PATH", str(BASE_DIR / "data" / "ops.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_cursor():
    conn = get_db()
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS dashboard_stats (
        id INTEGER PRIMARY KEY,
        online_count INTEGER,
        total_token_usage INTEGER,
        monthly_tasks INTEGER,
        system_load INTEGER,
        task_success_rate REAL,
        token_efficiency REAL,
        task_trend_change REAL,
        success_rate_change REAL
    );

    CREATE TABLE IF NOT EXISTS status_dist (
        id INTEGER PRIMARY KEY,
        status TEXT,
        label TEXT,
        count INTEGER,
        color TEXT
    );

    CREATE TABLE IF NOT EXISTS token_daily (
        id INTEGER PRIMARY KEY,
        date TEXT,
        value REAL
    );

    CREATE TABLE IF NOT EXISTS task_detail (
        id INTEGER PRIMARY KEY,
        dates TEXT,   -- JSON array
        success TEXT, -- JSON array
        failed TEXT   -- JSON array
    );

    CREATE TABLE IF NOT EXISTS capability_dist (
        id INTEGER PRIMARY KEY,
        role TEXT,
        alias TEXT,
        dept TEXT,
        pct INTEGER
    );

    CREATE TABLE IF NOT EXISTS activity_log (
        id TEXT PRIMARY KEY,
        type TEXT,
        employee_id TEXT,
        alias TEXT,
        role TEXT,
        dept TEXT,
        content TEXT,
        timestamp TEXT
    );

    CREATE TABLE IF NOT EXISTS blueprints (
        id TEXT PRIMARY KEY,
        role TEXT,
        alias TEXT,
        department TEXT,
        versions TEXT,  -- JSON array of version objects
        capacity TEXT   -- JSON {used, max}
    );

    CREATE TABLE IF NOT EXISTS tools (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS task_executions (
        id TEXT PRIMARY KEY,
        run_id TEXT,
        blueprint_id TEXT,
        alias TEXT,
        role TEXT,
        dept TEXT,
        message TEXT,
        status TEXT,          -- ok | error
        token_input INTEGER,
        token_analysis INTEGER,
        token_completion INTEGER,
        token_total INTEGER,
        duration_ms INTEGER,
        summary TEXT,
        created_at TEXT       -- ISO timestamp
    );

    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        description TEXT DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 1
    );
    """)
    try:
        conn.execute("ALTER TABLE blueprints ADD COLUMN openclaw_agent_id TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Add avatar config columns
    try:
        conn.execute("ALTER TABLE blueprints ADD COLUMN soul_content TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute("ALTER TABLE blueprints ADD COLUMN agents_content TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute("ALTER TABLE blueprints ADD COLUMN user_content TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute("ALTER TABLE blueprints ADD COLUMN tools_enabled TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute("ALTER TABLE blueprints ADD COLUMN selected_model TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.commit()
    conn.close()

    # Add missing columns to existing tables (idempotent)
    conn2 = get_db()
    cur2 = conn2.cursor()
    try:
        cur2.execute("ALTER TABLE task_executions ADD COLUMN response_text TEXT")
        conn2.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn2.close()

    seed_data()
    seed_tools()


def seed_data():
    conn = get_db()
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM dashboard_stats")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # Dashboard stats
    cur.execute("""
        INSERT INTO dashboard_stats (online_count, total_token_usage, monthly_tasks,
        system_load, task_success_rate, token_efficiency, task_trend_change, success_rate_change)
        VALUES (10, 19480000, 4513, 68, 94.2, 3.2, -8.7, 2.1)
    """)

    # Status distribution
    status_items = [
        ("active", "正式上岗", 10, "#4A7C59"),
        ("shadow", "试用期", 4, "#C47A3D"),
        ("sandbox", "沙盒态", 2, "#9A9490"),
        ("archived", "退役", 2, "#A8A29E"),
    ]
    cur.executemany(
        "INSERT INTO status_dist (status, label, count, color) VALUES (?, ?, ?, ?)",
        status_items,
    )

    # Token daily
    import json

    token_data = [
        ("03-27", 1.82),
        ("03-28", 2.34),
        ("03-29", 1.56),
        ("03-30", 0.98),
        ("03-31", 3.12),
        ("04-01", 2.78),
        ("04-02", 1.64),
    ]
    cur.executemany(
        "INSERT INTO token_daily (date, value) VALUES (?, ?)",
        token_data,
    )

    # Task detail
    cur.execute(
        """
        INSERT INTO task_detail (dates, success, failed) VALUES (?, ?, ?)
    """,
        (
            json.dumps(["03-27", "03-28", "03-29", "03-30", "03-31", "04-01", "04-02"]),
            json.dumps([138, 187, 106, 82, 221, 191, 111]),
            json.dumps([7, 11, 6, 5, 13, 10, 7]),
        ),
    )

    # Capability distribution
    cap_items = [
        ("数据分析师", "小龙", "商业智能部", 73),
        ("内容创作员", "墨白", "市场部", 18),
        ("运维工程师", "铁柱", "基础设施部", 6),
        ("客服专员", "小红", "客服部", 3),
    ]
    cur.executemany(
        "INSERT INTO capability_dist (role, alias, dept, pct) VALUES (?, ?, ?, ?)",
        cap_items,
    )

    # Activity log
    now = time.time()
    activities = [
        (
            "act-001",
            "task_completed",
            "EMP-015",
            "小龙",
            "数据分析师",
            "商业智能部",
            "完成了「月度数据标注质量报告」",
            now - 180,
        ),
        ("act-002", "shadow_pass", "EMP-002", "小红", "客服专员", "客服部", "试用期产出比对通过", now - 1080),
        ("act-003", "employee_joined", None, "建国", "知识库管理员", "数智部", "新员工入职（沙盒态）", now - 3600),
        (
            "act-004",
            "task_failed",
            "EMP-005",
            "铁柱",
            "运维工程师",
            "基础设施部",
            "任务执行失败，请检查日志",
            now - 7200,
        ),
        (
            "act-005",
            "task_completed",
            "EMP-013",
            "雅婷",
            "产品经理",
            "产品部",
            "完成了「用户调研报告 v2.3」",
            now - 10800,
        ),
        (
            "act-006",
            "task_completed",
            "EMP-007",
            "浩宇",
            "算法工程师",
            "研发部",
            "完成了「推荐算法准确性验证」",
            now - 18000,
        ),
        ("act-007", "status_changed", "EMP-016", "静怡", "品牌设计师", "市场部", "状态变更为「试用期」", now - 28800),
        (
            "act-008",
            "task_completed",
            "EMP-012",
            "凯文",
            "前端工程师",
            "研发部",
            "完成了「前端组件库升级评估」",
            now - 43200,
        ),
    ]
    import datetime

    for act in activities:
        ts = datetime.datetime.fromtimestamp(act[7]).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur.execute(
            "INSERT INTO activity_log (id,type,employee_id,alias,role,dept,content,timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (act[0], act[1], act[2], act[3], act[4], act[5], act[6], ts),
        )

    # Blueprints
    blueprints_data = [
        {
            "id": "av-admin-001",
            "role": "行政专员",
            "alias": "小白",
            "department": "综合管理部",
            "versions": [
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
            "capacity": {"used": 6, "max": 10},
        },
        {
            "id": "av-legal-001",
            "role": "法务专员",
            "alias": "明律",
            "department": "法务合规部",
            "versions": [
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
            "capacity": {"used": 1, "max": 5},
        },
        {
            "id": "av-contract-001",
            "role": "合同专员",
            "alias": "墨言",
            "department": "商务运营部",
            "versions": [
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
            "capacity": {"used": 2, "max": 5},
        },
        {
            "id": "av-swe-001",
            "role": "软件工程师",
            "alias": "码哥",
            "department": "技术研发部",
            "versions": [
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
            "capacity": {"used": 5, "max": 10},
        },
    ]

    for bp in blueprints_data:
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

def seed_tools():
    """Seed OpenClaw built-in tools if tools table is empty."""
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


def get_blueprint_config(bp_id: str):
    """Return full avatar config for a blueprint."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, role, alias, department, openclaw_agent_id,
                  soul_content, agents_content, user_content,
                  tools_enabled, selected_model
           FROM blueprints WHERE id = ?""",
        (bp_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    import json
    return {
        "id": row[0], "role": row[1], "alias": row[2], "department": row[3],
        "openclaw_agent_id": row[4] or row[0],
        "soul_content": row[5] or "", "agents_content": row[6] or "",
        "user_content": row[7] or "", "tools_enabled": json.loads(row[8] or "[]"),
        "selected_model": row[9] or "",
    }

def save_blueprint_config(bp_id: str, config: dict):
    """Save avatar config fields for a blueprint.

    Only updates fields that are not None in the config dict.
    This allows partial updates (only changed fields) without overwriting others.
    """
    import json
    conn = get_db()
    cur = conn.cursor()

    # Build dynamic UPDATE: only set fields that are present (not None)
    set_clauses = []
    params = []
    if "soul_content" in config:
        set_clauses.append("soul_content = ?")
        params.append(config["soul_content"])
    if "agents_content" in config:
        set_clauses.append("agents_content = ?")
        params.append(config["agents_content"])
    if "user_content" in config:
        set_clauses.append("user_content = ?")
        params.append(config["user_content"])
    if "tools_enabled" in config:
        set_clauses.append("tools_enabled = ?")
        params.append(json.dumps(config["tools_enabled"]))
    if "selected_model" in config:
        set_clauses.append("selected_model = ?")
        params.append(config["selected_model"])

    if set_clauses:
        params.append(bp_id)
        cur.execute(f"UPDATE blueprints SET {', '.join(set_clauses)} WHERE id = ?", params)
        conn.commit()
    conn.close()


def record_execution(
    run_id: str,
    blueprint_id: str,
    message: str,
    status: str,
    token_input: int,
    token_analysis: int,
    token_completion: int,
    duration_ms: int,
    summary: str,
    response_text: str = "",
) -> str:
    """Record a single task execution and update aggregated dashboard_stats."""
    exec_id = f"exec-{uuid.uuid4().hex[:10]}"
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO task_executions "
        "(id,run_id,blueprint_id,message,status,"
        "token_input,token_analysis,token_completion,duration_ms,summary,response_text,created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            exec_id,
            run_id,
            blueprint_id,
            message,
            status,
            token_input,
            token_analysis,
            token_completion,
            duration_ms,
            summary,
            response_text,
            created_at,
        ),
    )

    _recalc_stats(conn)
    conn.commit()
    conn.close()
    return exec_id


def _recalc_stats(conn: sqlite3.Connection) -> None:
    """Recalculate dashboard_stats from task_executions and activity_log."""
    cur = conn.cursor()

    # Token totals: real executions + seed baseline
    cur.execute("""
        SELECT COALESCE(SUM(token_input + token_analysis + token_completion), 0) AS total_tokens,
               COUNT(*) AS total_tasks,
               SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END) AS success_count
        FROM task_executions
    """)
    row = cur.fetchone()
    # Seed baseline: 19480000 tokens, 4513 tasks, 4242 successes
    total_tokens = row["total_tokens"] + 19480000
    total_tasks = row["total_tasks"] + 4513
    success_count = row["success_count"] + 4242

    # Task trend: count tasks per day (last 7 days)
    now_ts = datetime.now(timezone.utc)
    days = [(now_ts - timedelta(days=i)).strftime("%m-%d") for i in reversed(range(7))]
    daily_counts = []
    for day in days:
        cur.execute(
            "SELECT COUNT(*) FROM task_executions WHERE created_at LIKE ?",
            (f"%{day}%",),
        )
        daily_counts.append(cur.fetchone()[0] or 0)

    # task_trend_change: compare last 2 days
    task_trend_change = 0.0
    if len(daily_counts) >= 2:
        prev, curr = daily_counts[-2], daily_counts[-1]
        task_trend_change = round((curr - prev) / max(prev, 1) * 100, 1)

    success_rate = round(success_count / max(total_tasks, 1) * 100, 1)
    token_efficiency = round(total_tasks / max(total_tokens / 1_000_000, 1), 2)

    cur.execute(
        """
        UPDATE dashboard_stats SET
            total_token_usage  = ?,
            monthly_tasks      = ?,
            task_success_rate  = ?,
            token_efficiency   = ?,
            task_trend_change  = ?,
            success_rate_change = COALESCE(
                ? - (SELECT task_success_rate FROM dashboard_stats LIMIT 1), 0)
        WHERE id = (SELECT id FROM dashboard_stats LIMIT 1)
    """,
        (
            total_tokens,
            total_tasks,
            success_rate,
            token_efficiency,
            task_trend_change,
            success_rate,
        ),
    )

    # Append today's task counts to task_detail
    today = now_ts.strftime("%m-%d")
    cur.execute("SELECT dates, success, failed FROM task_detail LIMIT 1")
    td_row = cur.fetchone()
    if td_row:
        dates = json.loads(td_row["dates"])
        success = json.loads(td_row["success"])
        failed = json.loads(td_row["failed"])
        today_success = sum(
            1
            for r in conn.execute(
                "SELECT 1 FROM task_executions WHERE status='ok' AND created_at LIKE ?", (f"%{today}%",)
            ).fetchall()
        )
        today_failed = sum(
            1
            for r in conn.execute(
                "SELECT 1 FROM task_executions WHERE status!='ok' AND created_at LIKE ?", (f"%{today}%",)
            ).fetchall()
        )
        if dates and dates[-1] == today:
            success[-1] = (success[-1] or 0) + today_success
            failed[-1] = (failed[-1] or 0) + today_failed
        else:
            dates.append(today)
            success.append(today_success)
            failed.append(today_failed)
        if len(dates) > 30:
            dates, success, failed = dates[-30:], success[-30:], failed[-30:]
        cur.execute(
            "UPDATE task_detail SET dates=?, success=?, failed=?",
            (json.dumps(dates), json.dumps(success), json.dumps(failed)),
        )


def get_recent_executions(limit: int = 10):
    """Return recent task executions for the activity feed, joining with blueprints for latest alias."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id, t.blueprint_id, b.alias, b.role, b.department, t.message, t.status,
               t.token_input, t.token_analysis, t.token_completion, t.duration_ms, t.summary, t.response_text, t.created_at
        FROM task_executions t
        LEFT JOIN blueprints b ON t.blueprint_id = b.id
        ORDER BY t.created_at DESC LIMIT ?
        """,
        (limit,),
    )
    rows = [
        {
            "id": r[0],
            "blueprint_id": r[1],
            "alias": r[2],
            "role": r[3],
            "dept": r[4],
            "message": r[5],
            "status": r[6],
            "token_input": r[7],
            "token_analysis": r[8],
            "token_completion": r[9],
            "duration_ms": r[10],
            "summary": r[11],
            "response_text": r[12],
            "created_at": r[13],
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows
