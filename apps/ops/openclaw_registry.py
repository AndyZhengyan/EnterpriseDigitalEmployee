"""Openclaw agent directory management — auto-create/update agent configs from blueprints."""

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw"

logger = structlog.get_logger("openclaw_registry")


def generate_soul_md(
    blueprint_id: str,
    alias: str,
    role: str,
    department: str,
    soul: Dict[str, Any],
) -> str:
    """Generate SOUL.md content from blueprint data."""
    description = soul.get("description", f"{alias}，{role}。")
    communication_style = soul.get("communication_style", "专业、结构化")

    return f"""\
# SOUL.md — Who I Am

> {alias}（{role}）。{department}。

---

## Core Identity [LOCKED]

**Name:** {alias}
**Role:** {role}
**Department:** {department}
**Blueprint ID:** {blueprint_id}

**Personality:**
{description}

**Voice:**
- 专业、结构化
- {communication_style}

## Working Style [AUTONOMOUS]

**Primary Responsibilities:**
- 以 {role} 身份处理 {department} 相关任务
- 遵循部门规范和流程

---

## Evolution Log
Created from blueprint `{blueprint_id}` via e-agent-os.

---

_此文件由 e-agent-os 自动创建，请勿手工修改。_
"""


class OpenclawAgentRegistry:
    """Manages openclaw agent directories for e-agent-os blueprints."""

    def __init__(
        self,
        openclaw_dir: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
    ):
        self.openclaw_dir = openclaw_dir or DEFAULT_OPENCLAW_DIR
        self.agents_dir = agents_dir or (self.openclaw_dir / "agents")

    def register_agent(
        self,
        blueprint_id: str,
        alias: str,
        role: str,
        department: str,
        soul: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create or update agent directory for a blueprint."""
        soul = soul or {}
        agent_dir = self.agents_dir / blueprint_id / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write SOUL.md
        soul_md = generate_soul_md(blueprint_id, alias, role, department, soul)
        (agent_dir / "SOUL.md").write_text(soul_md, encoding="utf-8")

        # 2. Copy auth-profiles.json and models.json from a template agent
        self._copy_agent_configs(agent_dir)

        logger.info(
            "agent_registered",
            blueprint_id=blueprint_id,
            alias=alias,
            agent_dir=str(agent_dir),
        )
        return True

    def remove_agent(self, blueprint_id: str) -> bool:
        """Delete agent directory for a blueprint."""
        agent_dir = self.agents_dir / blueprint_id
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
            logger.info("agent_removed", blueprint_id=blueprint_id)
        return True

    def _copy_agent_configs(self, target_dir: Path) -> None:
        """Copy auth-profiles.json and models.json from an existing agent as template."""
        for existing in self.agents_dir.iterdir():
            # Skip the target itself (newly created agent has its blueprint_id as dir name)
            if existing.name == target_dir.parent.name:
                continue
            existing_agent = existing / "agent"
            if existing_agent.is_dir():
                auth_profiles = existing_agent / "auth-profiles.json"
                models = existing_agent / "models.json"
                if auth_profiles.exists():
                    target = target_dir / "auth-profiles.json"
                    if not target.exists():
                        target.write_bytes(auth_profiles.read_bytes())
                if models.exists():
                    target = target_dir / "models.json"
                    if not target.exists():
                        target.write_bytes(models.read_bytes())
                return

        logger.warning("no_template_agent_found", fallback=True)
        (target_dir / "auth-profiles.json").write_text("{}")
        (target_dir / "models.json").write_text("{}")
