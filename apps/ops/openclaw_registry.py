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
    ) -> tuple[bool, str]:
        """Register agent with openclaw CLI and set up its directory.

        Returns (success, openclaw_agent_id) where openclaw_agent_id is the
        normalized ID that openclaw uses (e.g. 'av---123' for 'av-行政专员-123').
        """
        import re
        import subprocess

        soul = soul or {}
        agent_dir = self.agents_dir / blueprint_id / "agent"
        workspace_dir = self.agents_dir / blueprint_id / "workspace"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # 1. Register with openclaw CLI (idempotent — skips if already registered)
        normalized_id = blueprint_id  # fallback to original if CLI call fails
        try:
            result = subprocess.run(
                [
                    "openclaw",
                    "agents",
                    "add",
                    blueprint_id,
                    "--agent-dir",
                    str(agent_dir),
                    "--workspace",
                    str(workspace_dir),
                    "--non-interactive",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                # Parse the normalized agent ID from openclaw output
                # e.g. "Normalized agent id to \"av---1775915029\""
                for line in (result.stdout + result.stderr).splitlines():
                    m = re.search(r'Normalized agent id to "?([^"]+)"?', line)
                    if m:
                        normalized_id = m.group(1)
                        break
                logger.info(
                    "agent_registered_via_cli",
                    blueprint_id=blueprint_id,
                    openclaw_agent_id=normalized_id,
                    alias=alias,
                )
            else:
                stderr = result.stderr.strip()
                if "already exists" not in stderr.lower():
                    logger.warning(
                        "agent_register_cli_partial",
                        blueprint_id=blueprint_id,
                        stderr=stderr[:200],
                    )
        except Exception as e:
            logger.warning("agent_register_cli_failed", blueprint_id=blueprint_id, error=str(e))

        # 2. Write SOUL.md
        soul_md = generate_soul_md(blueprint_id, alias, role, department, soul)
        (agent_dir / "SOUL.md").write_text(soul_md, encoding="utf-8")

        # 3. Copy auth-profiles.json and models.json from a template agent
        self._copy_agent_configs(agent_dir)

        logger.info(
            "agent_setup_complete",
            blueprint_id=blueprint_id,
            openclaw_agent_id=normalized_id,
            alias=alias,
            agent_dir=str(agent_dir),
        )
        return True, normalized_id

    def remove_agent(self, blueprint_id: str) -> bool:
        """Remove agent from openclaw config and delete its directory.

        Uses direct config manipulation (the canonical openclaw "agents delete" flow)
        so we avoid CLI hangs from gateway/credential prompts.
        """
        import json

        # 1. Remove from openclaw.json agents.list
        config_path = self.openclaw_dir / "openclaw.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                agents_list = cfg.get("agents", {}).get("list", [])
                before = len(agents_list)
                agents_list = [a for a in agents_list if a.get("id") != blueprint_id]
                if len(agents_list) < before:
                    cfg["agents"]["list"] = agents_list
                    # Write backup then update
                    bak = config_path.with_suffix(".json.bak")
                    shutil.copy2(config_path, bak)
                    with open(config_path, "w") as f:
                        json.dump(cfg, f, indent=2, ensure_ascii=False)
                    f.write("\n")  # trailing newline
                    logger.info("agent_removed_from_config", blueprint_id=blueprint_id)
            except Exception as e:
                logger.warning("agent_config_edit_failed", blueprint_id=blueprint_id, error=str(e))

        # 2. Remove agent directory tree
        agent_dir = self.agents_dir / blueprint_id
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
            logger.info("agent_dir_removed", blueprint_id=blueprint_id)

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
