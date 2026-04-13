# apps/ops/main.py — Ops Center API (Dashboard + Onboarding + PiAgent)
import datetime
import json
import os
import re
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from common.tracing import get_logger as _ops_get_logger

from .db import (
    BASE_DIR,
    get_db,
    get_recent_executions,
    init_db,
    record_execution,
    get_blueprint_config,
    save_blueprint_config,
)
from .key_manager import OPSKeyManager
from .openclaw_registry import OpenclawAgentRegistry
from .tools_registry import list_tools, create_tool, update_tool, delete_tool
from .avatar_assembler import write_avatar_files, get_assembled_config

_key_manager: Optional[OPSKeyManager] = None


def get_key_manager() -> OPSKeyManager:
    global _key_manager
    if _key_manager is None:
        raise RuntimeError("Key manager not initialized")
    return _key_manager


def _init_key_manager(db_path: str) -> None:
    """Initialize the key manager with the given DB path. Idempotent — skips if already initialized."""
    global _key_manager
    if _key_manager is not None:
        return
    _key_manager = OPSKeyManager(db_path=db_path)
    _key_manager.init_db()
    _key_manager.ensure_key_exists()


def _force_dev_mode() -> None:
    """Force dev mode by deactivating any active DB key. For test use only."""
    global _key_manager
    if _key_manager is not None:
        import sqlite3

        conn = sqlite3.connect(_key_manager.db_path)
        conn.execute("UPDATE api_keys SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        conn.close()


def verify_api_key(x_api_key: str = Header(default="")):
    if _key_manager is None:
        return True  # Uninitialized = dev mode
    if os.environ.get("OPS_API_KEY"):
        # Explicit env key — always verify against it
        if not _key_manager.verify_key(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True
    # No env key set — dev mode: allow requests without a key
    # (auto-generated DB keys are for UI/API clients, not for headless test callers)
    if x_api_key:
        # A key was provided — verify it against the DB key if one exists
        if not _key_manager.verify_key(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True


CORS_ORIGINS = os.environ.get("OPS_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


_runner_active = False
_log = _ops_get_logger("ops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — OPSKeyManager
    global _key_manager
    db_path = os.environ.get("OPS_DB_PATH", "data/ops.db")
    _key_manager = OPSKeyManager(db_path=db_path)
    _key_manager.init_db()
    _key_manager.ensure_key_exists()
    # Startup — original init
    init_db()
    yield


app = FastAPI(
    title="AvatarOS Ops API",
    description="AvatarOS 运营数据 + 入职中心 API + PiAgent 集成",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_gateway_token() -> str:
    """Read gateway token from openclaw config or env."""
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if token:
        return token
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
            return cfg.get("gateway", {}).get("auth", {}).get("token", "")
    except Exception:
        return ""


def _normalize_openclaw_id(agent_id: str) -> str:
    """Strip non-ASCII chars so openclaw can find the normalized agent ID.

    openclaw normalizes agent IDs (removes Chinese/non-ASCII chars) when they are
    registered via `openclaw agents add`. For example, 'av-行政专员-123'
    becomes 'av---123'. We must use the normalized form when calling openclaw.
    """
    return agent_id.encode("ascii", "ignore").decode("ascii")


def _run_piagent(message: str, agent_id: str = "chat", timeout: int = 60) -> Dict[str, Any]:
    """Call openclaw CLI (pi-agent) and return parsed JSON result. Stub for CI."""
    import uuid

    # CI stub — openclaw CLI not available in GitHub Actions runner
    if os.environ.get("PIAGENT_CLI_STUB") == "true":
        return {
            "status": "ok",
            "runId": f"stub-{uuid.uuid4().hex[:8]}",
            "summary": "CI stub response — this is a simulated agent execution",
            "result": {
                "meta": {
                    "agentMeta": {
                        "usage": {"input": 1200, "output": 340, "cacheRead": 0},
                        "durationMs": 2100,
                    }
                }
            },
        }

    normalized_id = _normalize_openclaw_id(agent_id)
    token = _get_gateway_token()
    gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "OPENCLAW_GATEWAY_TOKEN": token,
        "OPENCLAW_GATEWAY_URL": gateway_url,
    }
    try:
        result = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent",
                normalized_id,
                "--message",
                message,
                "--json",
                "--thinking",
                "medium",
                "--timeout",
                str(timeout),
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            env=env,
            check=False,
        )
        # openclaw writes JSON response to stdout; stderr may contain config warnings
        stdout_output = result.stdout.strip()
        if not stdout_output:
            # Fall back to stderr (some configs may write JSON there)
            fallback_output = result.stderr.strip()
            if not fallback_output:
                return {"status": "error", "summary": "Empty response", "usage": {}}
            json_start = fallback_output.find("{")
            if json_start == -1:
                if result.returncode == 0:
                    return {"status": "error", "summary": f"No JSON in output: {fallback_output[:200]}", "usage": {}}
                return {"status": "error", "summary": f"CLI error: {fallback_output[:200]}", "usage": {}}
            parsed = json.loads(fallback_output[json_start:])
        else:
            parsed = json.loads(stdout_output)
        # Extract the actual response text for the user
        # Paths: result.payloads[0].text (primary) or result.meta.finalAssistantVisibleText (fallback)
        result_block = parsed.get("result", {})
        payloads = result_block.get("payloads")
        text = (
            payloads[0].get("text", "")
            if payloads
            else result_block.get("meta", {}).get("finalAssistantVisibleText", "")
        )
        # "NO_REPLY" means the agent ran but produced no visible output — treat as empty
        if text == "NO_REPLY":
            text = ""
        parsed["responseText"] = text
        return parsed
    except FileNotFoundError:
        return {"status": "error", "summary": "openclaw CLI not found in PATH", "usage": {}}
    except subprocess.TimeoutExpired:
        return {"status": "error", "summary": "Execution timed out", "usage": {}}
    except json.JSONDecodeError as e:
        return {"status": "error", "summary": f"Invalid JSON: {e}", "usage": {}}
    except Exception as e:
        return {"status": "error", "summary": str(e), "usage": {}}


# ── Admin: API Key Management ────────────────────────────────


@app.post("/api/admin/api-key")
def create_api_key(req: dict, _: bool = Depends(verify_api_key)):
    """Generate a new API key. Returns the plaintext key ONCE — store it securely."""
    description = req.get("description", "")
    key = get_key_manager().generate_and_store(description)
    return {
        "key": key,
        "hint": get_key_manager().get_active_key_hint(),
        "warning": "This key is shown only once. Store it securely.",
    }


@app.get("/api/admin/api-key/hint")
def get_api_key_hint(_: bool = Depends(verify_api_key)):
    """Get a hint about the current active key (no secrets exposed)."""
    return {"hint": get_key_manager().get_active_key_hint()}


# ── Dashboard ────────────────────────────────────────────────


@app.get("/api/dashboard/stats")
def get_stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT online_count, total_token_usage, monthly_tasks, system_load,
               task_success_rate, token_efficiency, task_trend_change, success_rate_change
        FROM dashboard_stats LIMIT 1
    """)
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


@app.get("/api/dashboard/status-dist")
def get_status_dist():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, label, count, color FROM status_dist")
    rows = [{"status": r[0], "label": r[1], "count": r[2], "color": r[3]} for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/dashboard/token-trend")
def get_token_trend():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT date, value FROM token_daily ORDER BY date")
    rows = [{"date": r[0], "value": r[1]} for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/dashboard/task-detail")
def get_task_detail():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT dates, success, failed FROM task_detail LIMIT 1")
    row = cur.fetchone()
    row = {"dates": row[0], "success": row[1], "failed": row[2]}
    conn.close()
    return {
        "dates": json.loads(row["dates"]),
        "success": json.loads(row["success"]),
        "failed": json.loads(row["failed"]),
    }


@app.get("/api/dashboard/task-trend")
def get_task_trend(_: bool = Depends(verify_api_key)):
    """Returns task trend as [{date, value}] for the TaskTrend chart component."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT dates, success, failed FROM task_detail LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return []
    dates = json.loads(row[0])
    success = json.loads(row[1])
    # Return success counts as trend data
    return [{"date": d, "value": s} for d, s in zip(dates, success)]


@app.get("/api/dashboard/token-daily")
def get_token_daily():
    return get_token_trend()


@app.get("/api/dashboard/capability-dist")
def get_capability_dist():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT role, alias, dept, pct FROM capability_dist ORDER BY pct DESC")
    rows = [{"role": r[0], "alias": r[1], "dept": r[2], "pct": r[3]} for r in cur.fetchall()]
    conn.close()
    return rows


@app.get("/api/dashboard/activity")
def get_activity(limit: int = 10):
    # Blend real executions with seed activity_log
    executions = get_recent_executions(limit=limit)

    activity_items = []
    for ex in executions:
        activity_items.append(
            {
                "id": ex["id"],
                "type": "task_completed" if ex["status"] == "ok" else "task_failed",
                "employeeId": ex["blueprint_id"],
                "employeeName": ex["alias"],
                "role": ex["role"],
                "dept": ex["dept"],
                "content": ex["summary"] or ex["message"][:60],
                "timestamp": ex["created_at"],
            }
        )

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
                    "employeeId": r[2],
                    "employeeName": r[3],
                    "role": r[4],
                    "dept": r[5],
                    "content": r[6],
                    "timestamp": r[7],
                }
            )
        conn.close()

    # Sort by timestamp descending, take top `limit`
    activity_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return activity_items[:limit]


# ── PiAgent Execute ────────────────────────────────────────────


@app.post("/api/ops/execute")
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


# ── Onboarding ────────────────────────────────────────────────


@app.get("/api/onboarding/blueprints")
def get_blueprints(_: bool = Depends(verify_api_key)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, role, alias, department, versions, capacity FROM blueprints")
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "role": r[1],
            "alias": r[2],
            "department": r[3],
            "versions": json.loads(r[4]),
            "capacity": json.loads(r[5]),
        }
        for r in rows
    ]


@app.post("/api/onboarding/deploy")
def deploy_avatar(req: dict, _: bool = Depends(verify_api_key)):
    """Deploy a new avatar and auto-create openclaw agent directory."""
    bp_id = f"av-{req['role']}-{int(time.time())}"
    scaling = req["scaling"]
    soul = req.get("soul", {})
    new_version = {
        "version": "v1.0.0",
        "status": "published",
        "traffic": 100,
        "replicas": scaling["minReplicas"],
        "config": {
            "soul": soul,
            "skills": req.get("skills", []),
            "tools": req.get("tools", []),
            "model": req.get("model", ""),
        },
        "scaling": scaling,
    }

    # Create openclaw agent and get the normalized ID openclaw uses internally
    openclaw_dir = Path(os.environ.get("OPENCLAW_DIR", str(os.path.expanduser("~/.openclaw"))))
    agents_dir = openclaw_dir / "agents"
    registry = OpenclawAgentRegistry(openclaw_dir=openclaw_dir, agents_dir=agents_dir)
    try:
        _, openclaw_agent_id = registry.register_agent(
            blueprint_id=bp_id,
            alias=req["alias"],
            role=req["role"],
            department=req["department"],
            soul=soul,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create openclaw agent: {e}")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO blueprints "
        "(id, role, alias, department, versions, capacity, openclaw_agent_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            bp_id,
            req["role"],
            req["alias"],
            req["department"],
            json.dumps([new_version]),
            json.dumps({"used": scaling["minReplicas"], "max": scaling["maxReplicas"]}),
            openclaw_agent_id,
        ),
    )
    conn.commit()
    conn.close()
    return {
        "id": bp_id,
        "role": req["role"],
        "alias": req["alias"],
        "department": req["department"],
        "versions": [new_version],
        "capacity": {"used": scaling["minReplicas"], "max": scaling["maxReplicas"]},
    }


@app.put("/api/onboarding/blueprints/{bp_id}/traffic")
def update_traffic(bp_id: str, req: dict, _: bool = Depends(verify_api_key)):
    """更新指定版本的 traffic 权重。"""
    version_idx = req.get("version_index")
    new_traffic = req.get("traffic")
    if new_traffic is None or version_idx is None:
        raise HTTPException(status_code=400, detail="version_index and traffic are required")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, versions, capacity FROM blueprints WHERE id = ?", (bp_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blueprint not found")

    versions = json.loads(row[1])
    if version_idx < 0 or version_idx >= len(versions):
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid version_index")

    versions[version_idx]["traffic"] = new_traffic

    total_used = sum(v["replicas"] for v in versions if v["traffic"] > 0)
    capacity = json.loads(row[2])
    capacity["used"] = total_used

    cur.execute(
        "UPDATE blueprints SET versions = ?, capacity = ? WHERE id = ?",
        (json.dumps(versions), json.dumps(capacity), bp_id),
    )
    conn.commit()
    conn.close()

    return {"id": bp_id, "versions": versions, "capacity": capacity}


@app.put("/api/onboarding/blueprints/{bp_id}/versions/{idx}/deprecate")
def deprecate_version(bp_id: str, idx: int, _: bool = Depends(verify_api_key)):
    """将指定版本下线（traffic=0, status=deprecated）。"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, versions, capacity FROM blueprints WHERE id = ?", (bp_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blueprint not found")

    versions = json.loads(row[1])
    if idx < 0 or idx >= len(versions):
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid version index")

    versions[idx]["traffic"] = 0
    versions[idx]["status"] = "deprecated"

    total_used = sum(v["replicas"] for v in versions if v["traffic"] > 0)
    capacity = json.loads(row[2])
    capacity["used"] = total_used

    cur.execute(
        "UPDATE blueprints SET versions = ?, capacity = ? WHERE id = ?",
        (json.dumps(versions), json.dumps(capacity), bp_id),
    )
    conn.commit()
    conn.close()

    return {"id": bp_id, "versions": versions, "capacity": capacity}


@app.delete("/api/onboarding/blueprints/{bp_id}")
def delete_blueprint(bp_id: str, _: bool = Depends(verify_api_key)):
    """Delete blueprint and its openclaw agent directory."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM blueprints WHERE id = ?", (bp_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Blueprint not found")
    cur.execute("DELETE FROM blueprints WHERE id = ?", (bp_id,))
    conn.commit()
    conn.close()

    # Clean up openclaw agent
    openclaw_dir = Path(os.environ.get("OPENCLAW_DIR", str(os.path.expanduser("~/.openclaw"))))
    agents_dir = openclaw_dir / "agents"
    registry = OpenclawAgentRegistry(openclaw_dir=openclaw_dir, agents_dir=agents_dir)
    registry.remove_agent(bp_id)

    return {"deleted": bp_id}


# ── Enablement ──────────────────────────────────────────────────────────────


@app.get("/enablement/tools")
def get_tools():
    return list_tools()


@app.post("/enablement/tools")
def post_tools(req: dict):
    name = req.get("name", "").strip()
    description = req.get("description", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    result = create_tool(name, description)
    if result is None:
        raise HTTPException(status_code=409, detail="Tool name already exists")
    return result


@app.put("/enablement/tools/{tool_id}")
def put_tools(tool_id: str, req: dict):
    description = req.get("description", "").strip()
    result = update_tool(tool_id, description)
    if not result:
        raise HTTPException(status_code=404, detail="Tool not found")
    return result


@app.delete("/enablement/tools/{tool_id}")
def del_tools(tool_id: str):
    if not delete_tool(tool_id):
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"message": "deleted"}


# ── Avatar Config API ────────────────────────────────────────────────────────


@app.get("/onboarding/blueprints/{bp_id}/config")
def get_avatar_config(bp_id: str, _: bool = Depends(verify_api_key)):
    """Get full avatar config for a blueprint, merging DB fields + assembled files."""
    db_config = get_blueprint_config(bp_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    # Merge with live file content. Files are at bp_id path, not openclaw_agent_id path.
    agent_id = db_config.get("id") or bp_id
    file_content = get_assembled_config(agent_id)
    return {**db_config, **file_content}


@app.put("/onboarding/blueprints/{bp_id}/config")
def put_avatar_config(bp_id: str, config: dict, _: bool = Depends(verify_api_key)):
    """Save avatar config to DB and write OpenClaw .md files.

    Uses None as sentinel: only fields present in request (not None) are updated.
    This prevents auto-generated content from being saved back to DB when user
    only changes one field.
    """
    db_config = get_blueprint_config(bp_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    # Save only fields that were explicitly provided (not None)
    save_blueprint_config(bp_id, config)
    # Write to OpenClaw files: merge db identity fields + REQUEST config fields.
    # config has user-provided values (from PUT body); db_config has id/openclaw_agent_id.
    full_config = {**db_config, **config}
    write_avatar_files(full_config)
    return {"message": "saved", "blueprint_id": bp_id}


# ─── Test Support ────────────────────────────────────────────────────────────


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

SEED_CAPACITY = {
    "av-admin-001": {"used": 6, "max": 10},
    "av-legal-001": {"used": 1, "max": 5},
    "av-contract-001": {"used": 2, "max": 5},
    "av-swe-001": {"used": 5, "max": 10},
}


@app.post("/api/test/reset-seeds")
def reset_seed_blueprints(_: bool = Depends(verify_api_key)):
    """Reset all seed blueprints to their original versions and traffic.
    Used by E2E tests to ensure consistent state before each test."""
    conn = get_db()
    cur = conn.cursor()
    for bp_id, versions in SEED_VERSIONS.items():
        total_used = sum(v["replicas"] for v in versions if v["traffic"] > 0)
        capacity = dict(SEED_CAPACITY[bp_id])
        capacity["used"] = total_used
        cur.execute(
            "UPDATE blueprints SET versions = ?, capacity = ? WHERE id = ?",
            (json.dumps(versions), json.dumps(capacity), bp_id),
        )
    conn.commit()
    conn.close()
    return {"reset": "ok", "seeds": list(SEED_VERSIONS.keys())}


# ── Journal — Audit Log ────────────────────────────────────────


@app.get("/api/journal/executions")
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
        params.extend([f"%{q}%", f"%{q}%"])
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    cur.execute(f"SELECT COUNT(*) FROM task_executions WHERE {where_sql}", params)
    total = cur.fetchone()[0]
    cur.execute(
        f"""
        SELECT t.id, t.run_id, t.blueprint_id, b.alias, b.role, b.department, t.message,
               t.status, t.token_input, t.token_completion, t.token_analysis,
               t.duration_ms, t.summary, t.response_text, t.created_at
        FROM task_executions t
        LEFT JOIN blueprints b ON t.blueprint_id = b.id
        WHERE {where_sql}
        ORDER BY t.created_at DESC
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


@app.get("/api/journal/executions/{exec_id}")
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


# ── Oracle — Knowledge Archive ─────────────────────────────────


ORACLE_DIR = Path(os.environ.get("ORACLE_DIR", str(BASE_DIR / "data" / "oracle")))


def _read_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown string. Returns (meta_dict, body_string)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content
    meta = yaml.safe_load(content[4:end]) or {}
    body = content[end + 5 :]
    return meta, body


def _scan_archives(source_filter: str | None = None) -> list[dict]:
    """Scan oracle directories for .md files and return their metadata."""
    archives = []
    dirs_to_scan = ["avatar", "import"] if not source_filter else [source_filter]
    for sd in dirs_to_scan:
        d = ORACLE_DIR / sd
        if not d.is_dir():
            continue
        for f in d.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            meta, body = _read_frontmatter(content)
            slug = f.stem
            # Extract summary: first non-empty line of body, stripped, max 100 chars
            summary = ""
            if body:
                first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
                summary = first_line[:100]
            archives.append(
                {
                    "id": slug,
                    "title": meta.get("title", slug),
                    "source": sd,
                    "contributor": meta.get("contributor", ""),
                    "createdAt": meta.get("created_at", ""),
                    "tags": meta.get("tags", []),
                    "summary": summary,
                }
            )
    return sorted(archives, key=lambda a: a.get("createdAt", ""), reverse=True)


@app.get("/api/oracle/archives")
def list_archives(source: str | None = None, _: bool = Depends(verify_api_key)):
    """List all archives, optionally filtered by source (avatar | import)."""
    items = _scan_archives(source_filter=source)
    return {"total": len(items), "items": items}


@app.get("/api/oracle/archives/{archive_id}")
def get_archive(archive_id: str, _: bool = Depends(verify_api_key)):
    """Get a single archive by slug (filename without .md). archive_id is URL-decoded."""
    archive_id = unquote(archive_id)
    for sd in ["avatar", "import"]:
        fp = ORACLE_DIR / sd / f"{archive_id}.md"
        if fp.exists():
            content = fp.read_text(encoding="utf-8")
            meta, body = _read_frontmatter(content)
            return {
                "id": archive_id,
                "title": meta.get("title", archive_id),
                "source": sd,
                "contributor": meta.get("contributor", ""),
                "createdAt": meta.get("created_at", ""),
                "tags": meta.get("tags", []),
                "content": body.strip(),
            }
    raise HTTPException(status_code=404, detail="Archive not found")


@app.post("/api/oracle/archives/upload")
def upload_archive(req: dict, _: bool = Depends(verify_api_key)):
    """Upload a new archive. Creates a .md file under data/oracle/{source}/."""
    title = req.get("title", "").strip()
    source = req.get("source", "import")
    body_content = req.get("content", "")
    contributor = req.get("contributor", "管理员")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if source not in ("avatar", "import"):
        raise HTTPException(status_code=400, detail="source must be 'avatar' or 'import'")
    safe_slug = re.sub(r"[^\w\s-]", "", title).replace(" ", "-").replace("\n", "-")
    created_at = datetime.date.today().isoformat()
    fp = ORACLE_DIR / source / f"{safe_slug}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    if fp.exists():
        raise HTTPException(status_code=409, detail="Archive with this title already exists")
    fm_dict = {
        "title": title,
        "source": source,
        "contributor": contributor,
        "created_at": created_at,
        "tags": [],
    }
    fm = yaml.safe_dump(fm_dict, allow_unicode=True, default_flow_style=False)
    fp.write_text(f"---\n{fm}---\n\n" + "\n" + body_content, encoding="utf-8")
    return {"id": safe_slug, "path": str(fp.relative_to(ORACLE_DIR)), "message": "上传成功"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
