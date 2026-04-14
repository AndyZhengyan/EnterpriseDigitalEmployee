"""Persistent task store backed by SQLite.

Replaces the in-memory _task_store in main.py so task state survives process restarts.
Follows the same sqlite3 pattern as apps/ops/db.py.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DB_PATH = os.environ.get("RUNTIME_DB_PATH", str(_DB_DIR / "runtime_tasks.db"))

# Thread-local write lock to make the single-connection approach safe across
# FastAPI's async workers (each worker owns its own connection; the lock protects
# against concurrent writes within a single worker).
_lock = threading.RLock()


def _get_conn() -> sqlite3.Connection:
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _conn_ctx():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _rows_to_task(row: sqlite3.Row) -> Dict[str, Any]:
    """Deserialize a task row into the same dict shape that _task_store used."""
    task = json.loads(row["data"])
    task["_id"] = row["id"]
    return task


class TaskStore:
    """Persistent task store using SQLite.

    Matches the dict-based interface that main.py's _task_store exposed so
    callers (main.py) need no changes — only the underlying storage is swapped.

    Thread-safe for concurrent reads; writes are serialized via a lock.
    """

    @staticmethod
    def init() -> None:
        """Create the tasks table and indexes. Idempotent — safe to call on every start."""
        with _conn_ctx() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_tasks (
                    id          TEXT    PRIMARY KEY,
                    data        TEXT    NOT NULL,   -- JSON-serialized task dict
                    created_at  TEXT    NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runtime_tasks_created ON runtime_tasks(created_at)")

    @staticmethod
    def create_task(task_id: str, status: str, employee_id: str, **kwargs) -> Dict[str, Any]:
        """Insert a new task record. Returns the task dict (same shape as before)."""
        task = {
            "task_id": task_id,
            "status": status,
            "employee_id": employee_id,
            "created_at": datetime.now(timezone.utc),
            "started_at": None,
            "completed_at": None,
            "steps": [],
            "current_step": 0,
            "total_steps": 0,
            "trace_id": kwargs.pop("trace_id", ""),
            **kwargs,
        }
        with _lock, _conn_ctx() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runtime_tasks (id, data, created_at) VALUES (?, ?, ?)",
                (task_id, json.dumps(task, default=str), datetime.now(timezone.utc).isoformat()),
            )
        return task

    @staticmethod
    def get_task(task_id: str) -> Optional[Dict[str, Any]]:
        """Return the task dict, or None if not found."""
        with _conn_ctx() as conn:
            row = conn.execute("SELECT id, data FROM runtime_tasks WHERE id = ?", (task_id,)).fetchone()
        if row:
            return _rows_to_task(row)
        return None

    @staticmethod
    def update_task(task_id: str, **updates) -> None:
        """Merge updates into an existing task. No-op if task doesn't exist."""
        existing = TaskStore.get_task(task_id)
        if existing is None:
            return
        existing.update(updates)
        with _lock, _conn_ctx() as conn:
            conn.execute(
                "UPDATE runtime_tasks SET data = ? WHERE id = ?",
                (json.dumps(existing, default=str), task_id),
            )

    @staticmethod
    def delete_task(task_id: str) -> None:
        """Remove a task record."""
        with _lock, _conn_ctx() as conn:
            conn.execute("DELETE FROM runtime_tasks WHERE id = ?", (task_id,))

    @staticmethod
    def list_tasks() -> List[Dict[str, Any]]:
        """Return all tasks ordered by created_at desc."""
        with _conn_ctx() as conn:
            rows = conn.execute("SELECT id, data FROM runtime_tasks ORDER BY created_at DESC").fetchall()
        return [_rows_to_task(r) for r in rows]

    @staticmethod
    def clear() -> None:
        """Delete all tasks. Used on shutdown."""
        with _lock, _conn_ctx() as conn:
            conn.execute("DELETE FROM runtime_tasks")

    @staticmethod
    def active_count() -> int:
        """Count tasks with status == 'running'."""
        tasks = TaskStore.list_tasks()
        return sum(1 for t in tasks if t.get("status") == "running")

    @staticmethod
    def total_count() -> int:
        """Count all tasks."""
        with _conn_ctx() as conn:
            row = conn.execute("SELECT COUNT(*) FROM runtime_tasks").fetchone()
        return row[0] if row else 0

    @staticmethod
    def close() -> None:
        """Clean up resources (no-op for sqlite3; kept for interface symmetry)."""
        pass
