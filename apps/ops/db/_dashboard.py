"""Dashboard query helpers — stats, trends, and activity feed."""

from __future__ import annotations

import json

from ._executions import get_recent_executions
from ._schema import get_db


def get_status_dist() -> list[dict]:
    """Return status distribution rows for dashboard."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, label, count, color FROM status_dist")
    rows = [{"status": r[0], "label": r[1], "count": r[2], "color": r[3]} for r in cur.fetchall()]
    conn.close()
    return rows


def get_capability_dist() -> list[dict]:
    """Return capability distribution rows for dashboard."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT role, alias, dept, pct FROM capability_dist ORDER BY pct DESC")
    rows = [{"role": r[0], "alias": r[1], "dept": r[2], "pct": r[3]} for r in cur.fetchall()]
    conn.close()
    return rows


def get_task_detail() -> dict:
    """Return task detail dates/success/failed arrays."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT dates, success, failed FROM task_detail LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"dates": [], "success": [], "failed": []}
    return {
        "dates": json.loads(row[0]),
        "success": json.loads(row[1]),
        "failed": json.loads(row[2]),
    }


def get_task_trend() -> list[dict]:
    """Return task trend as [{date, value}] for the TaskTrend chart."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT dates, success, failed FROM task_detail LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return []
    dates = json.loads(row[0])
    success = json.loads(row[1])
    return [{"date": d, "value": s} for d, s in zip(dates, success)]


def get_token_daily() -> list[dict]:
    """Return token daily trend rows."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT date, value FROM token_daily ORDER BY date")
    rows = [{"date": r[0], "value": r[1]} for r in cur.fetchall()]
    conn.close()
    return rows


def get_activity_feed(limit: int = 10) -> list[dict]:
    """Blend real executions with seed activity_log, sorted by timestamp descending."""
    executions = get_recent_executions(limit=limit)

    activity_items = [
        {
            "id": ex["id"],
            "type": "task_completed" if ex["status"] == "ok" else "task_failed",
            "alias": ex["alias"],
            "role": ex["role"],
            "dept": ex["dept"],
            "content": ex["summary"] or ex["message"][:60],
            "timestamp": ex["created_at"],
        }
        for ex in executions
    ]

    if len(activity_items) < limit:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, type, employee_id, alias, role, dept, content, timestamp "
            "FROM activity_log ORDER BY timestamp DESC LIMIT ?",
            (limit - len(activity_items),),
        )
        for r in cur.fetchall():
            activity_items.append(
                {
                    "id": r[0],
                    "type": r[1],
                    "alias": r[3],
                    "role": r[4],
                    "dept": r[5],
                    "content": r[6],
                    "timestamp": r[7],
                }
            )
        conn.close()

    activity_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return activity_items[:limit]
