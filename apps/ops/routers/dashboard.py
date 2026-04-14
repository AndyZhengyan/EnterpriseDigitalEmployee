# apps/ops/routers/dashboard.py — Dashboard stats, activity feed, and trend charts

from fastapi import APIRouter, Depends

from apps.ops._auth import verify_api_key
from apps.ops.db import get_activity_feed, get_capability_dist, get_status_dist, get_token_daily
from apps.ops.db import get_task_detail as _get_task_detail
from apps.ops.db import get_task_trend as _get_task_trend

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(_: bool = Depends(verify_api_key)):
    from apps.ops.db import get_db

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT online_count, total_token_usage, monthly_tasks, system_load,
               task_success_rate, token_efficiency, task_trend_change, success_rate_change
        FROM dashboard_stats LIMIT 1
    """
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {
            "onlineCount": 0,
            "totalTokenUsage": 0,
            "monthlyTasks": 0,
            "systemLoad": 0.0,
            "taskSuccessRate": 0.0,
            "tokenEfficiency": 0.0,
            "taskTrend": {"change": 0, "direction": "up"},
            "tokenTrendChange": 0,
            "successRateChange": 0,
        }
    direction = "down" if row[6] < 0 else "up"
    return {
        "onlineCount": row[0],
        "totalTokenUsage": row[1],
        "monthlyTasks": row[2],
        "systemLoad": row[3],
        "taskSuccessRate": row[4],
        "tokenEfficiency": row[5],
        "taskTrend": {"change": row[6], "direction": direction},
        "tokenTrendChange": row[6],
        "successRateChange": row[7],
    }


@router.get("/status-dist")
def get_status_distribution():
    return get_status_dist()


@router.get("/token-trend")
def get_token_trend():
    from apps.ops.db import get_db

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT date, value FROM token_daily ORDER BY date")
    rows = [{"date": r[0], "value": r[1]} for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/token-daily")
def get_token_daily_route():
    return get_token_daily()


@router.get("/task-detail")
def get_task_detail():
    return _get_task_detail()


@router.get("/task-trend")
def get_task_trend(_: bool = Depends(verify_api_key)):
    return _get_task_trend()


@router.get("/capability-dist")
def get_capability_distribution():
    return get_capability_dist()


@router.get("/activity")
def get_activity(limit: int = 10):
    return get_activity_feed(limit=limit)
