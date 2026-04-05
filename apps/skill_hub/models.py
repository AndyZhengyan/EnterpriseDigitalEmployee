"""SkillHub request/response models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    """Skill tier / level."""

    L1 = "L1"  # Enterprise通用技能
    L2 = "L2"  # 岗位专用技能
    L3 = "L3"  # 场景临时技能


class SkillStatus(str, Enum):
    """Skill lifecycle status."""

    DRAFT = "draft"
    TESTING = "testing"
    STAGING = "staging"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


# Valid lifecycle transitions
VALID_TRANSITIONS: dict[SkillStatus, list[SkillStatus]] = {
    SkillStatus.DRAFT: [SkillStatus.TESTING],
    SkillStatus.TESTING: [SkillStatus.STAGING, SkillStatus.DRAFT],
    SkillStatus.STAGING: [SkillStatus.PUBLISHED, SkillStatus.TESTING],
    SkillStatus.PUBLISHED: [SkillStatus.DEPRECATED],
    SkillStatus.DEPRECATED: [],  # Terminal state
}


class Skill(BaseModel):
    """Skill descriptor — mirrors common.models.Skill."""

    id: str
    name: str
    description: str = ""
    level: SkillLevel = SkillLevel.L2
    version: str = "1.0"
    capabilities: List[Any] = Field(default_factory=list)  # re-export SkillCapability from common
    agent_families: List[str] = Field(default_factory=list)
    status: SkillStatus = SkillStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"use_enum_values": True, "extra": "ignore"}


class RegisterSkillRequest(BaseModel):
    """Request to register a new skill."""

    id: str = Field(..., description="Unique skill ID")
    name: str
    description: str = ""
    level: SkillLevel = SkillLevel.L2
    capabilities: List[Any] = Field(default_factory=list)
    agent_families: List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class SkillListResponse(BaseModel):
    """Response for GET /skills."""

    skills: List[Skill]
    total: int


class InvokeRequest(BaseModel):
    """Request to invoke a skill."""

    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=600)
    employee_id: Optional[str] = None

    model_config = {"extra": "ignore"}


class InvokeResponse(BaseModel):
    """Response for skill invocation."""

    skill_id: str
    result: Any = None
    duration_ms: int = 0
    error: Optional[str] = None

    model_config = {"extra": "ignore"}


class TransitionRequest(BaseModel):
    """Request to transition skill lifecycle status."""

    target_status: SkillStatus

    model_config = {"extra": "ignore"}


class SkillHubHealthResponse(BaseModel):
    """Response for GET /skill-hub/health."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    skill_count: int = 0

    model_config = {"extra": "ignore"}
