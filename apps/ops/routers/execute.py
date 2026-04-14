# apps/ops/routers/execute.py — PiAgent execution via openclaw CLI

from fastapi import APIRouter, Depends, HTTPException

from apps.ops._auth import verify_api_key
from apps.ops._piagent import _run_piagent
from apps.ops.db import get_db, record_execution

router = APIRouter(prefix="/api/ops", tags=["execute"])


@router.post("/execute")
def execute_task(req: dict, _: bool = Depends(verify_api_key)):
    """
    Execute a task via PiAgent (openclaw CLI) and record the result.
    Returns the PiAgent execution result plus the internal exec_id.
    """
    message = req.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    agent_id = req.get("blueprint_id", "av-swe-001")
    bp_id = agent_id

    # Look up the blueprint details (alias, role, dept) and openclaw agent ID from DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT alias, role, department, openclaw_agent_id FROM blueprints WHERE id = ?", (bp_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    alias, role, dept, openclaw_agent_id = row
    # Use normalized ID if set, otherwise fall back to original (pre-migration blueprints)
    if not openclaw_agent_id:
        openclaw_agent_id = agent_id

    raw = _run_piagent(message, openclaw_agent_id, timeout=120)

    # openclaw JSON: meta lives under result.meta
    meta = raw.get("result", {}).get("meta", {})
    usage = meta.get("agentMeta", {}).get("usage", {})
    token_input = usage.get("input", 0)
    token_analysis = usage.get("cacheRead", 0)
    token_completion = usage.get("output", 0)
    status = raw.get("status", "ok")
    run_id = meta.get("agentMeta", {}).get("sessionId", "") or raw.get("runId", "")
    response_text = raw.get("responseText", "")
    summary = response_text[:200] if response_text else raw.get("summary", "")
    duration_ms = meta.get("durationMs", 0)

    exec_id = record_execution(
        run_id=run_id or "",
        blueprint_id=bp_id,
        message=message,
        status=status,
        token_input=token_input,
        token_analysis=token_analysis,
        token_completion=token_completion,
        duration_ms=duration_ms,
        summary=summary[:200] if summary else "",
        response_text=response_text,
    )

    return {
        "execId": exec_id,
        "runId": run_id,
        "status": status,
        "summary": summary,
        "responseText": response_text,
        "tokenInput": token_input,
        "tokenAnalysis": token_analysis,
        "tokenCompletion": token_completion,
        "tokenTotal": token_input + token_analysis + token_completion,
        "durationMs": duration_ms,
        "alias": alias,
        "role": role,
        "dept": dept,
    }
