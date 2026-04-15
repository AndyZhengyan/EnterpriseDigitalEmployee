"""Schema definitions and DDL — all CREATE TABLE and ALTER statements."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = __import__("os").environ.get("OPS_DB_PATH", str(BASE_DIR / "data" / "ops.db"))


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


_DDL = """
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
"""

# Idempotent ALTER statements run after DDL.
# Format: (sql, description) — description is for documentation only.
_ALTERS = [
    # blueprints additions
    ("ALTER TABLE blueprints ADD COLUMN openclaw_agent_id TEXT", "openclaw agent id"),
    ("ALTER TABLE blueprints ADD COLUMN soul_content TEXT DEFAULT ''", "soul config content"),
    ("ALTER TABLE blueprints ADD COLUMN agents_content TEXT DEFAULT ''", "agents config content"),
    ("ALTER TABLE blueprints ADD COLUMN user_content TEXT DEFAULT ''", "user config content"),
    ("ALTER TABLE blueprints ADD COLUMN tools_enabled TEXT DEFAULT '[]'", "enabled tool list"),
    ("ALTER TABLE blueprints ADD COLUMN selected_model TEXT DEFAULT ''", "selected model name"),
    # task_executions additions
    ("ALTER TABLE task_executions ADD COLUMN response_text TEXT", "execution response text"),
]


def run_schema():
    """Run all DDL + idempotent ALTER statements."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.executescript(_DDL)

    for sql, _desc in _ALTERS:
        try:
            cur.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.commit()
    conn.close()
