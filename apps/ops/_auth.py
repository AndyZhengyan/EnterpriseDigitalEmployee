# apps/ops/_auth.py — Key manager and verify_api_key dependency
# Extracted from main.py to avoid circular imports with routers.
import os
import sqlite3
from typing import Optional

from fastapi import Header, HTTPException

from .key_manager import OPSKeyManager

_key_manager: Optional[OPSKeyManager] = None
_is_dev_mode: bool = False  # set True by _force_dev_mode()


def get_key_manager() -> OPSKeyManager:
    global _key_manager
    if _key_manager is None:
        raise RuntimeError("Key manager not initialized")
    return _key_manager


def _init_key_manager(db_path: str) -> None:
    """Initialize the key manager with the given DB path. Idempotent."""
    global _key_manager
    if _key_manager is not None:
        return
    _key_manager = OPSKeyManager(db_path=db_path)
    _key_manager.init_db()
    _key_manager.ensure_key_exists()


def _force_dev_mode() -> None:
    """Force dev mode by deactivating any active DB key. For test use only."""
    global _is_dev_mode, _key_manager
    _is_dev_mode = True
    if _key_manager is not None:
        conn = sqlite3.connect(_key_manager.db_path)
        conn.execute("UPDATE api_keys SET is_active = 0 WHERE is_active = 1")
        conn.commit()
        conn.close()


def verify_api_key(x_api_key: str = Header(default="")) -> bool:
    """Dependency: verify the API key for protected endpoints."""
    global _key_manager, _is_dev_mode
    # Explicit dev mode override — all requests pass without a key
    if _is_dev_mode:
        return True
    if _key_manager is None:
        return True  # Uninitialized = dev mode
    if os.environ.get("OPS_API_KEY"):
        if not _key_manager.verify_key(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True
    if x_api_key:
        if not _key_manager.verify_key(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True
