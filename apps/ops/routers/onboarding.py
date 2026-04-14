# apps/ops/routers/onboarding.py — Blueprint management, deploy, traffic, deprecate
import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from apps.ops._auth import verify_api_key
from apps.ops.db import get_db
from apps.ops.openclaw_registry import OpenclawAgentRegistry

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/blueprints")
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


@router.post("/deploy")
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


@router.put("/blueprints/{bp_id}/traffic")
def update_traffic(bp_id: str, req: dict, _: bool = Depends(verify_api_key)):
    """Update traffic weight for a specific version."""
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


@router.put("/blueprints/{bp_id}/versions/{idx}/deprecate")
def deprecate_version(bp_id: str, idx: int, _: bool = Depends(verify_api_key)):
    """Deprecate a specific version (traffic=0, status=deprecated)."""
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


@router.delete("/blueprints/{bp_id}")
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
