# apps/ops/routers/tools_registry.py — Tools shelf CRUD endpoints
from fastapi import APIRouter, HTTPException

from apps.ops.tools_registry import create_tool, delete_tool, list_tools, update_tool

router = APIRouter(prefix="/enablement", tags=["tools"])


@router.get("/tools")
def get_tools():
    return list_tools()


@router.post("/tools")
def post_tools(req: dict):
    name = req.get("name", "").strip()
    description = req.get("description", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    result = create_tool(name, description)
    if result is None:
        raise HTTPException(status_code=409, detail="Tool name already exists")
    return result


@router.put("/tools/{tool_id}")
def put_tools(tool_id: str, req: dict):
    description = req.get("description", "").strip()
    result = update_tool(tool_id, description)
    if not result:
        raise HTTPException(status_code=404, detail="Tool not found")
    return result


@router.delete("/tools/{tool_id}")
def del_tools(tool_id: str):
    if not delete_tool(tool_id):
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"message": "deleted"}
