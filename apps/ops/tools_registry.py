# apps/ops/tools_registry.py
import sqlite3

from apps.ops.db import get_db


def list_tools():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, created_at FROM tools ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "description": r[2], "created_at": r[3]} for r in rows]


def create_tool(name: str, description: str) -> dict:
    import uuid
    from datetime import datetime, timezone

    conn = get_db()
    cur = conn.cursor()
    tool_id = f"custom-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        cur.execute(
            "INSERT INTO tools (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (tool_id, name, description, created_at),
        )
    except sqlite3.IntegrityError:
        conn.close()
        return None  # name already exists
    conn.commit()
    conn.close()
    return {"id": tool_id, "name": name, "description": description, "created_at": created_at}


def update_tool(tool_id: str, description: str) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tools SET description = ? WHERE id = ?", (description, tool_id))
    conn.commit()
    cur.execute("SELECT id, name, description, created_at FROM tools WHERE id = ?", (tool_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "description": row[2], "created_at": row[3]}


def delete_tool(tool_id: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0
