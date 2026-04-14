# apps/ops/routers/avatar.py — Avatar config GET/PUT (SOUL/IDENTITY/AGENT file assembly)
from fastapi import APIRouter, Depends, HTTPException

from apps.ops._auth import verify_api_key
from apps.ops.avatar_assembler import get_assembled_config, write_avatar_files
from apps.ops.db import get_blueprint_config, save_blueprint_config

router = APIRouter(prefix="/onboarding/blueprints", tags=["avatar"])


@router.get("/{bp_id}/config")
def get_avatar_config(bp_id: str, _: bool = Depends(verify_api_key)):
    """Get full avatar config for a blueprint, merging DB fields + assembled files."""
    db_config = get_blueprint_config(bp_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    # Merge with live file content. Files are at bp_id path, not openclaw_agent_id path.
    agent_id = db_config.get("id") or bp_id
    file_content = get_assembled_config(agent_id)
    return {**db_config, **file_content}


@router.put("/{bp_id}/config")
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
