# apps/ops/routers/journal.py — Execution log / audit trail

from fastapi import APIRouter, Depends, HTTPException

from apps.ops._auth import verify_api_key
from apps.ops.db import get_db

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("/executions")
def list_executions(
    start_date: str | None = None,
    end_date: str | None = None,
    roles: str | None = None,
    depts: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _: bool = Depends(verify_api_key),
):
    """Query task executions with filters."""
    limit = min(limit, 200)
    conn = get_db()
    cur = conn.cursor()
    where_clauses = []
    params = []
    if start_date:
        where_clauses.append("created_at >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("created_at <= ?")
        params.append(end_date)
    if roles and roles != "all":
        role_list = [r.strip() for r in roles.split(",") if r.strip()]
        placeholders = ",".join("?" * len(role_list))
        where_clauses.append(f"role IN ({placeholders})")
        params.extend(role_list)
    if depts and depts != "all":
        dept_list = [d.strip() for d in depts.split(",") if d.strip()]
        placeholders = ",".join("?" * len(dept_list))
        where_clauses.append(f"dept IN ({placeholders})")
        params.extend(dept_list)
    if status and status != "all":
        where_clauses.append("status = ?")
        params.append(status)
    if q:
        where_clauses.append("(message LIKE ? OR summary LIKE ? OR response_text LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    cur.execute(f"SELECT COUNT(*) FROM task_executions WHERE {where_sql}", params)
    total = cur.fetchone()[0]
    cur.execute(
        f"""
        SELECT id, run_id, blueprint_id, alias, role, dept, message,
               status, token_input, token_completion, token_analysis,
               duration_ms, summary, response_text, created_at
        FROM task_executions
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )
    rows = cur.fetchall()
    conn.close()
    items = [
        {
            "id": r[0],
            "runId": r[1],
            "blueprintId": r[2],
            "alias": r[3],
            "role": r[4],
            "dept": r[5],
            "message": r[6],
            "status": r[7],
            "tokenInput": r[8],
            "tokenCompletion": r[9],
            "tokenAnalysis": r[10],
            "tokenTotal": (r[8] or 0) + (r[9] or 0) + (r[10] or 0),
            "durationMs": r[11],
            "summary": r[12],
            "responseText": r[13],
            "createdAt": r[14],
        }
        for r in rows
    ]
    return {"total": total, "items": items}


@router.get("/executions/{exec_id}")
def get_execution(exec_id: str, _: bool = Depends(verify_api_key)):
    """Get a single execution by ID with full detail."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.id, t.run_id, t.blueprint_id, b.alias, b.role, b.department, t.message,
           t.status, t.token_input, t.token_completion, t.token_analysis,
           t.duration_ms, t.summary, t.created_at
           FROM task_executions t
           LEFT JOIN blueprints b ON t.blueprint_id = b.id
           WHERE t.id = ?""",
        (exec_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {
        "id": row[0],
        "runId": row[1],
        "blueprintId": row[2],
        "alias": row[3],
        "role": row[4],
        "dept": row[5],
        "message": row[6],
        "status": row[7],
        "tokenInput": row[8],
        "tokenCompletion": row[9],
        "tokenAnalysis": row[10],
        "tokenTotal": (row[8] or 0) + (row[9] or 0) + (row[10] or 0),
        "durationMs": row[11],
        "summary": row[12],
        "createdAt": row[13],
    }
