# apps/ops/routers/admin.py — API key management
from fastapi import APIRouter, Depends

from apps.ops._auth import get_key_manager, verify_api_key

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/api-key")
def create_api_key(req: dict, _: bool = Depends(verify_api_key)):
    """Generate a new API key. Returns the plaintext key ONCE — store it securely."""
    description = req.get("description", "")
    key = get_key_manager().generate_and_store(description)
    return {
        "key": key,
        "hint": get_key_manager().get_active_key_hint(),
        "warning": "This key is shown only once. Store it securely.",
    }


@router.get("/api-key/hint")
def get_api_key_hint(_: bool = Depends(verify_api_key)):
    """Get a hint about the current active key (no secrets exposed)."""
    return {"hint": get_key_manager().get_active_key_hint()}
