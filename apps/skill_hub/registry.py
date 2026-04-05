"""SkillHub registry — manages skill lifecycle and discovery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.skill_hub.errors import SkillHubError, SkillNotFoundError
from apps.skill_hub.models import (
    VALID_TRANSITIONS,
    Skill,
    SkillLevel,
    SkillStatus,
)
from common.models import SkillCapability
from common.tracing import get_logger

log = get_logger("skill_hub.registry")

# Global registry: skill_id -> Skill
_registry: Dict[str, Skill] = {}


def register(skill: Skill) -> None:
    """Register a skill in the global registry."""
    if skill.id in _registry:
        log.warning("skill.already_registered", skill_id=skill.id)
    _registry[skill.id] = skill
    log.info("skill.registered", skill_id=skill.id, level=skill.level)


def get(skill_id: str) -> Skill:
    """Get a skill by ID."""
    if skill_id not in _registry:
        raise SkillNotFoundError(skill_id)
    return _registry[skill_id]


def list_all(
    status: Optional[SkillStatus] = None,
    level: Optional[SkillLevel] = None,
) -> List[Skill]:
    """List all skills, optionally filtered."""
    skills = list(_registry.values())
    if status is not None:
        skills = [s for s in skills if s.status == status]
    if level is not None:
        skills = [s for s in skills if s.level == level]
    return skills


def update_status(skill_id: str, target: SkillStatus) -> Skill:
    """Transition a skill to a new lifecycle status."""
    skill = get(skill_id)
    current = SkillStatus(skill.status)
    allowed = VALID_TRANSITIONS.get(current, [])

    if target not in allowed:
        raise SkillHubError(
            f"Invalid transition: {current.value} → {target.value}",
            skill_id=skill_id,
        )

    skill.status = target
    skill.updated_at = datetime.now(timezone.utc)
    log.info("skill.status_changed", skill_id=skill_id, from_=current.value, to=target.value)
    return skill


def _auto_seed() -> None:
    """Seed the registry with built-in L1 skills."""
    for skill_def in _BUILTIN_SKILLS:
        skill = Skill(
            id=str(skill_def["id"]),
            name=str(skill_def["name"]),
            description=str(skill_def["description"]),
            level=SkillLevel.L1,
            status=SkillStatus.PUBLISHED,
            capabilities=[
                SkillCapability(
                    name=str(c["name"]),
                    description=str(c["description"]),
                    idempotent=c.get("idempotent", True),
                )
                for c in skill_def.get("capabilities", [])
            ],
        )
        register(skill)
    log.info("skill_hub.seeded", count=len(_BUILTIN_SKILLS))


_BUILTIN_SKILLS: List[Dict[str, Any]] = [
    {
        "id": "builtin-approval",
        "name": "审批流程",
        "description": "企业审批流程 — 请假、报销、采购等",
        "capabilities": [
            {"name": "submit_approval", "description": "提交审批申请"},
            {"name": "query_status", "description": "查询审批状态"},
        ],
    },
    {
        "id": "builtin-notification",
        "name": "企业通知",
        "description": "飞书/邮件/短信多渠道通知",
        "capabilities": [
            {"name": "send_message", "description": "发送通知消息"},
            {"name": "send_bulk", "description": "批量发送通知"},
        ],
    },
    {
        "id": "builtin-email",
        "name": "邮件处理",
        "description": "邮件读取、发送、搜索",
        "capabilities": [
            {"name": "send_email", "description": "发送邮件"},
            {"name": "search_emails", "description": "搜索邮件"},
        ],
    },
]
