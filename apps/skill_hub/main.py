"""SkillHub FastAPI service — port 8004."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException

from apps.skill_hub import __version__
from apps.skill_hub.config import SkillHubSettings
from apps.skill_hub.errors import SkillHubError
from apps.skill_hub.models import (
    InvokeRequest,
    InvokeResponse,
    RegisterSkillRequest,
    Skill,
    SkillHubHealthResponse,
    SkillLevel,
    SkillListResponse,
    SkillStatus,
    TransitionRequest,
)
from apps.skill_hub.registry import (
    _auto_seed,
    get,
    list_all,
    register,
    update_status,
)
from common.tracing import get_logger

log = get_logger("skill_hub")

settings = SkillHubSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _auto_seed()
    log.info("skill_hub.started", port=settings.port, skill_count=len(list_all()))
    yield
    log.info("skill_hub.stopped")


app = FastAPI(title="SkillHub", version=__version__, lifespan=lifespan)


@app.get("/skill-hub/health", response_model=SkillHubHealthResponse)
async def hub_health() -> SkillHubHealthResponse:
    """Overall health of SkillHub."""
    return SkillHubHealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        skill_count=len(list_all()),
    )


@app.get("/skills", response_model=SkillListResponse)
async def list_skills(
    status: Optional[str] = None,
    level: Optional[str] = None,
) -> SkillListResponse:
    """List all registered skills, optionally filtered."""
    status_filter = SkillStatus(status) if status else None
    level_filter = SkillLevel(level) if level else None
    skills = list_all(status=status_filter, level=level_filter)
    return SkillListResponse(skills=skills, total=len(skills))


@app.post("/skills", response_model=Skill, status_code=201)
async def register_skill(req: RegisterSkillRequest) -> Skill:
    """Register a new skill."""
    skill = Skill(
        id=req.id,
        name=req.name,
        description=req.description,
        level=req.level,
        capabilities=req.capabilities,
        agent_families=req.agent_families,
        status=SkillStatus.DRAFT,
    )
    register(skill)
    log.info("skill.registered", skill_id=skill.id)
    return skill


@app.get("/skills/{skill_id}", response_model=Skill)
async def get_skill(skill_id: str) -> Skill:
    """Get a skill by ID."""
    try:
        return get(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")


@app.post("/skills/{skill_id}/transition", response_model=Skill)
async def transition_skill(
    skill_id: str,
    req: TransitionRequest,
) -> Skill:
    """Transition a skill to a new lifecycle status."""
    try:
        return update_status(skill_id, req.target_status)
    except SkillHubError as e:
        raise HTTPException(status_code=400, detail=e.message) from e


@app.post("/skills/{skill_id}/invoke", response_model=InvokeResponse)
async def invoke_skill(
    skill_id: str,
    req: InvokeRequest,
) -> InvokeResponse:
    """Invoke a skill by ID."""
    start = time.monotonic()

    try:
        skill = get(skill_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")

    if SkillStatus(skill.status) == SkillStatus.DEPRECATED:
        log.warning("skill.invoke.deprecated", skill_id=skill_id)
        return InvokeResponse(
            skill_id=skill_id,
            duration_ms=int((time.monotonic() - start) * 1000),
            error=f"Skill '{skill_id}' is deprecated",
        )

    duration_ms = int((time.monotonic() - start) * 1000)

    # Skill invocation is currently a stub — actual invocation would call
    # the ConnectorHub or external system. This returns a structured response.
    return InvokeResponse(
        skill_id=skill_id,
        result={"status": "not_implemented", "message": f"Skill '{skill_id}' invoke not yet connected"},
        duration_ms=duration_ms,
    )
