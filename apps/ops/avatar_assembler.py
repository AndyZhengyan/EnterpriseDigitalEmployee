# apps/ops/avatar_assembler.py
# Assemble structured avatar config into OpenClaw .md files
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

OPENCLAW_DIR = Path(os.environ.get("OPENCLAW_DIR", str(Path.home() / ".openclaw")))
AGENTS_DIR = OPENCLAW_DIR / "agents"

def _backup_file(filepath: Path):
    """Create timestamped backup before writing."""
    if filepath.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = filepath.parent / f"{filepath.name}.backup.{ts}"
        shutil.copy2(filepath, backup_path)

def _ensure_agent_dir(agent_id: str) -> Path:
    agent_dir = AGENTS_DIR / agent_id / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    return agent_dir

def assemble_identity(config: dict) -> str:
    """Assemble IDENTITY.md content."""
    return f"""# IDENTITY.md

> {config.get('alias', '')}（{config.get('role', '')}）。{config.get('department', '')}。

---

## Core Identity [LOCKED]

**Name:** {config.get('alias', '')}
**Role:** {config.get('role', '')}
**Department:** {config.get('department', '')}
**Blueprint ID:** {config.get('id', '')}

"""

def assemble_soul(config: dict) -> str:
    """Assemble SOUL.md content from soul_content field."""
    content = config.get("soul_content", "")
    if content:
        return content
    # Default minimal SOUL from identity
    return f"""# SOUL.md — Who I Am

> {config.get('alias', '')}（{config.get('role', '')}）。

---

## Core Identity [LOCKED]

**Name:** {config.get('alias', '')}
**Role:** {config.get('role', '')}
**Department:** {config.get('department', '')}

"""

def assemble_agents(config: dict) -> str:
    """Assemble AGENTS.md from agents_content or use minimal default."""
    content = config.get("agents_content", "")
    if content:
        return content
    return """# AGENTS.md — Constitution

> This file is your operating law.

## Session Protocol

1. Read `SOUL.md` — this is who you are
2. Read `USER.md` — this is who you are helping
3. Read `memory/` — recent context

"""

def assemble_user(config: dict) -> str:
    """Assemble USER.md from user_content."""
    content = config.get("user_content", "")
    if content:
        return content
    return f"""# USER.md

**称呼:** 用户
**时区:** Asia/Shanghai

## 沟通偏好

- 结论先行
- 简洁直接

"""

def assemble_tools(config: dict) -> str:
    """Assemble TOOLS.md with enabled tools list."""
    tools = config.get("tools_enabled", [])
    if not tools:
        return "# TOOLS.md\n\nNo tools enabled.\n"
    lines = ["# TOOLS.md\n", "## 已启用工具\n"]
    for tool in tools:
        lines.append(f"- **{tool}**")
    return "\n".join(lines) + "\n"

def write_avatar_files(config: dict):
    """Write all OpenClaw .md files for an avatar."""
    agent_id = config.get("openclaw_agent_id") or config.get("id")
    agent_dir = _ensure_agent_dir(agent_id)

    files = {
        "IDENTITY.md": assemble_identity(config),
        "SOUL.md": assemble_soul(config),
        "AGENTS.md": assemble_agents(config),
        "USER.md": assemble_user(config),
        "TOOLS.md": assemble_tools(config),
    }

    for filename, content in files.items():
        filepath = agent_dir / filename
        _backup_file(filepath)
        filepath.write_text(content, encoding="utf-8")

def get_assembled_config(agent_id: str) -> dict:
    """Read current .md files and return as structured dict."""
    agent_dir = AGENTS_DIR / agent_id / "agent"
    def read_md(name):
        p = agent_dir / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    return {
        "soul_content": read_md("SOUL.md"),
        "agents_content": read_md("AGENTS.md"),
        "user_content": read_md("USER.md"),
    }
