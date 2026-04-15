"""Blueprint CRUD — avatar config persistence."""

from __future__ import annotations

import json

from ._schema import get_db


def get_blueprint_config(bp_id: str) -> dict | None:
    """Return full avatar config for a blueprint."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, role, alias, department, openclaw_agent_id,
                  soul_content, agents_content, user_content,
                  tools_enabled, selected_model
           FROM blueprints WHERE id = ?""",
        (bp_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "role": row[1],
        "alias": row[2],
        "department": row[3],
        "openclaw_agent_id": row[4] or row[0],
        "soul_content": row[5] or "",
        "agents_content": row[6] or "",
        "user_content": row[7] or "",
        "tools_enabled": json.loads(row[8] or "[]"),
        "selected_model": row[9] or "",
    }


def save_blueprint_config(bp_id: str, config: dict) -> None:
    """Save avatar config fields for a blueprint.

    Only updates fields that are present (not None) in the config dict,
    allowing partial updates without overwriting other fields.
    """
    set_clauses = []
    params = []
    if "soul_content" in config:
        set_clauses.append("soul_content = ?")
        params.append(config["soul_content"])
    if "agents_content" in config:
        set_clauses.append("agents_content = ?")
        params.append(config["agents_content"])
    if "user_content" in config:
        set_clauses.append("user_content = ?")
        params.append(config["user_content"])
    if "tools_enabled" in config:
        set_clauses.append("tools_enabled = ?")
        params.append(json.dumps(config["tools_enabled"]))
    if "selected_model" in config:
        set_clauses.append("selected_model = ?")
        params.append(config["selected_model"])

    if not set_clauses:
        return

    conn = get_db()
    cur = conn.cursor()
    params.append(bp_id)
    cur.execute(f"UPDATE blueprints SET {', '.join(set_clauses)} WHERE id = ?", params)
    conn.commit()
    conn.close()
