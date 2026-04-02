"""Auth middleware — extracts AuthContext from JWT tokens."""

from __future__ import annotations

import jwt
from fastapi import HTTPException, Request

from apps.governance.config import GovernanceSettings
from apps.governance.models import AuthContext, Permission, Role
from apps.governance.rbac import has_permission

_settings: GovernanceSettings | None = None


def _get_settings() -> GovernanceSettings:
    global _settings
    if _settings is None:
        _settings = GovernanceSettings()
    return _settings


def get_auth_context(request: Request) -> AuthContext:
    """Extract and validate auth context from the current request."""
    settings = _get_settings()
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth[7:]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return AuthContext(
            user_id=payload.get("user_id", ""),
            tenant_id=payload.get("tenant_id", ""),
            role=Role(payload.get("role", "employee_user")),
            attributes=payload.get("attributes", {}),
            exp=payload.get("exp"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token payload: {e}")


def require_admin(request: Request) -> AuthContext:
    """Require ADMIN permission (FastAPI dependency)."""
    ctx = get_auth_context(request)
    if not has_permission(ctx.user_id, Permission.ADMIN, ctx.tenant_id):
        raise HTTPException(status_code=403, detail="Admin permission required")
    return ctx


def require_tenant_admin(request: Request) -> AuthContext:
    """Require TENANT_ADMIN or higher role (FastAPI dependency)."""
    ctx = get_auth_context(request)
    role_hierarchy = {
        Role.PLATFORM_ADMIN: 4,
        Role.TENANT_ADMIN: 3,
        Role.TENANT_OPERATOR: 2,
        Role.EMPLOYEE_USER: 1,
    }
    user_level = role_hierarchy.get(ctx.role, 0)
    if user_level < 3:
        raise HTTPException(status_code=403, detail="Tenant admin role required")
    return ctx


def require_platform_admin(request: Request) -> AuthContext:
    """Require PLATFORM_ADMIN role (FastAPI dependency)."""
    ctx = get_auth_context(request)
    if ctx.role != Role.PLATFORM_ADMIN:
        raise HTTPException(status_code=403, detail="Platform admin role required")
    return ctx
