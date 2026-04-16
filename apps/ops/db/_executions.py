"""Execution recording and aggregated stats recalculation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from ._schema import get_db


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


def _recalc_stats(conn) -> None:
    """Recalculate dashboard_stats from task_executions + seed baseline."""
    from .._seed_data import DASHBOARD_STATS_BASELINE

    cur = conn.cursor()
    baseline = DASHBOARD_STATS_BASELINE

    cur.execute("""
        SELECT COALESCE(SUM(token_input + token_analysis + token_completion), 0),
               COUNT(*),
               SUM(CASE WHEN status = 'ok' THEN 1 ELSE 0 END)
        FROM task_executions
    """)
    row = cur.fetchone()
    total_tokens = row[0] + baseline["total_token_usage"]
    total_tasks = row[1] + baseline["total_tasks"]
    success_count = row[2] + baseline["success_count"]

    # Daily task counts (last 7 days)
    now_ts = datetime.now(timezone.utc)
    days = [(now_ts - timedelta(days=i)).strftime("%m-%d") for i in reversed(range(7))]
    daily_counts = []
    for day in days:
        cur.execute(
            "SELECT COUNT(*) FROM task_executions WHERE created_at LIKE ?",
            (f"%{day}%",),
        )
        daily_counts.append(cur.fetchone()[0] or 0)

    if len(daily_counts) < 2:
        prev = curr = 0
    else:
        prev, curr = daily_counts[-2], daily_counts[-1]
    task_trend_change = round((curr - prev) / max(prev, 1) * 100, 1)
    success_rate = round(success_count / max(total_tasks, 1) * 100, 1)
    token_efficiency = round(total_tasks / max(total_tokens / 1_000_000, 1), 2)

    cur.execute(
        """
        UPDATE dashboard_stats SET
            total_token_usage   = ?,
            monthly_tasks       = ?,
            task_success_rate   = ?,
            token_efficiency    = ?,
            task_trend_change   = ?,
            success_rate_change = COALESCE(
                ? - (SELECT task_success_rate FROM dashboard_stats LIMIT 1), 0)
        WHERE id = (SELECT id FROM dashboard_stats LIMIT 1)
        """,
        (total_tokens, total_tasks, success_rate, token_efficiency, task_trend_change, success_rate),
    )

    # Append today's counts to task_detail
    today = now_ts.strftime("%m-%d")
    cur.execute("SELECT dates, success, failed FROM task_detail LIMIT 1")
    td_row = cur.fetchone()
    if td_row:
        dates = json.loads(td_row[0])
        success = json.loads(td_row[1])
        failed = json.loads(td_row[2])
        today_ok = sum(
            1
            for _ in conn.execute(
                "SELECT 1 FROM task_executions WHERE status='ok' AND created_at LIKE ?",
                (f"%{today}%",),
            ).fetchall()
        )
        today_err = sum(
            1
            for _ in conn.execute(
                "SELECT 1 FROM task_executions WHERE status!='ok' AND created_at LIKE ?",
                (f"%{today}%",),
            ).fetchall()
        )
        if dates and dates[-1] == today:
            success[-1] = (success[-1] or 0) + today_ok
            failed[-1] = (failed[-1] or 0) + today_err
        else:
            dates.append(today)
            success.append(today_ok)
            failed.append(today_err)
        if len(dates) > 30:
            dates, success, failed = dates[-30:], success[-30:], failed[-30:]
        cur.execute(
            "UPDATE task_detail SET dates=?, success=?, failed=?",
            (json.dumps(dates), json.dumps(success), json.dumps(failed)),
        )


def get_recent_executions(limit: int = 10) -> list[dict]:
    """Return recent task executions, joined with blueprints for alias/role/dept."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT t.id, t.blueprint_id, b.alias, b.role, b.department,
               t.message, t.status,
               t.token_input, t.token_analysis, t.token_completion,
               t.duration_ms, t.summary, t.response_text, t.created_at
        FROM task_executions t
        LEFT JOIN blueprints b ON t.blueprint_id = b.id
        ORDER BY t.created_at DESC LIMIT ?
        """,
        (limit,),
    )
    rows = []
    for r in cur.fetchall():
        rows.append(
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
        )
    conn.close()
    return rows
