# apps/ops/routers/__init__.py — Re-export all routers for convenient importing
from . import admin, avatar, dashboard, execute, journal, onboarding, oracle, tools_registry

__all__ = [
    "admin",
    "avatar",
    "dashboard",
    "execute",
    "journal",
    "onboarding",
    "oracle",
    "tools_registry",
]
