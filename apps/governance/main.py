"""Governance FastAPI service — port 8007."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import jwt
from fastapi import Depends, FastAPI, HTTPException

from apps.governance import __version__
from apps.governance.abac import _auto_seed as abac_seed
from apps.governance.abac import get_policy, list_policies, register_policy
from apps.governance.config import GovernanceSettings
from apps.governance.middleware import require_admin, require_platform_admin, require_tenant_admin
from apps.governance.models import (
    ABACPolicy,
    AuthContext,
    Permission,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PolicyCreateRequest,
    PolicyListResponse,
    Role,
    RoleAssignRequest,
    RoleListResponse,
    TokenResponse,
    UserRoleListResponse,
)
from apps.governance.rbac import (
    _auto_seed as rbac_seed,
)
from apps.governance.rbac import (
    assign_role,
    get_user_role,
    has_permission,
    list_roles,
    list_user_roles,
    revoke_role,
)
from common.tracing import get_logger

log = get_logger("governance")

settings = GovernanceSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    rbac_seed()
    abac_seed()
    log.info(
        "governance.started",
        port=settings.port,
        role_count=len(list_roles()),
        policy_count=len(list_policies()),
    )
    yield
    log.info("governance.stopped")


app = FastAPI(title="Governance", version=__version__, lifespan=lifespan)


# ============== Health ==============


@app.get("/governance/health")
async def health() -> dict:
    """Overall governance service health."""
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role_count": len(list_roles()),
        "policy_count": len(list_policies()),
    }


# ============== Token ==============


@app.post("/governance/token", response_model=TokenResponse, tags=["认证"])
async def create_token(user_id: str, tenant_id: str, role: Role) -> TokenResponse:
    """Issue a JWT token (dev/test only — production should use external IdP)."""
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role.value,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.jwt_expiry_seconds,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return TokenResponse(token=token, expires_in=settings.jwt_expiry_seconds)


# ============== Roles ==============


@app.get("/governance/roles", response_model=RoleListResponse, tags=["RBAC"])
async def list_all_roles() -> RoleListResponse:
    """List all available role definitions."""
    roles = list_roles()
    return RoleListResponse(roles=roles, total=len(roles))


@app.post("/governance/roles/assign", status_code=201, tags=["RBAC"])
async def assign_user_role(
    req: RoleAssignRequest,
    ctx: AuthContext = Depends(require_admin),
) -> dict:
    """Assign a role to a user (requires ADMIN permission)."""
    assign_role(
        user_id=req.user_id,
        role=req.role,
        tenant_id=req.tenant_id,
        assigned_by=ctx.user_id,
    )
    return {"assigned": True, "user_id": req.user_id, "role": req.role.value}


@app.delete("/governance/roles/{tenant_id}/{user_id}", status_code=204, tags=["RBAC"])
async def revoke_user_role(
    tenant_id: str,
    user_id: str,
    _: AuthContext = Depends(require_tenant_admin),
) -> None:
    """Revoke a user's role in a tenant."""
    if not revoke_role(user_id, tenant_id):
        raise HTTPException(status_code=404, detail="Role assignment not found")


@app.get("/governance/roles/{tenant_id}/{user_id}", tags=["RBAC"])
async def get_user_role_endpoint(tenant_id: str, user_id: str) -> dict:
    """Get a user's role in a specific tenant."""
    role_assignment = get_user_role(user_id, tenant_id)
    if role_assignment is None:
        raise HTTPException(status_code=404, detail=f"No role found for user '{user_id}' in tenant '{tenant_id}'")
    return role_assignment.model_dump(mode="json")


@app.get("/governance/roles/assignments", response_model=UserRoleListResponse, tags=["RBAC"])
async def list_all_assignments(
    _: AuthContext = Depends(require_platform_admin),
) -> UserRoleListResponse:
    """List all user-role assignments (platform_admin only)."""
    assignments = list_user_roles()
    return UserRoleListResponse(assignments=assignments, total=len(assignments))


# ============== ABAC Policies ==============


@app.get("/governance/policies", response_model=PolicyListResponse, tags=["ABAC"])
async def list_abac_policies() -> PolicyListResponse:
    """List all ABAC policies."""
    policies = list_policies()
    return PolicyListResponse(policies=policies, total=len(policies))


@app.post("/governance/policies", status_code=201, tags=["ABAC"])
async def create_policy(
    req: PolicyCreateRequest,
    _: AuthContext = Depends(require_tenant_admin),
) -> ABACPolicy:
    """Create a new ABAC policy (requires ADMIN permission)."""
    if get_policy(req.id):
        raise HTTPException(status_code=409, detail=f"Policy '{req.id}' already exists")
    policy = ABACPolicy(
        id=req.id,
        name=req.name,
        description=req.description,
        conditions=req.conditions,
        actions=req.actions,
        resources=req.resources,
        effect=req.effect,
        priority=req.priority,
        enabled=req.enabled,
    )
    register_policy(policy)
    log.info("governance.policy.created", policy_id=policy.id)
    return policy


@app.get("/governance/policies/{policy_id}", tags=["ABAC"])
async def get_abac_policy(policy_id: str) -> ABACPolicy:
    """Get a specific ABAC policy."""
    policy = get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return policy


# ============== Permission Check ==============


@app.post("/governance/permissions/check", response_model=PermissionCheckResponse, tags=["权限检查"])
async def check_permission(req: PermissionCheckRequest) -> PermissionCheckResponse:
    """Check if a user has permission for an action on a resource.

    Evaluates both RBAC (role/permission) and ABAC (attribute policy).
    """
    from apps.governance.abac import ABACEvaluator
    from apps.governance.rbac import get_user_role as rbac_get_user_role

    role_assignment = rbac_get_user_role(req.user_id, req.attributes.get("tenant_id", ""))
    evaluator = ABACEvaluator(role_assignment, req.attributes)

    # RBAC check
    try:
        perm = Permission(req.action)
    except ValueError:
        perm = Permission.READ

    if role_assignment:
        rbac_ok = has_permission(req.user_id, perm, role_assignment.tenant_id)
    else:
        rbac_ok = False

    # ABAC check
    abac_ok, reason, matched = evaluator.check(req.action, req.resource)

    allowed = rbac_ok and abac_ok
    final_reason = reason if not allowed else "Allowed by RBAC and ABAC"
    return PermissionCheckResponse(
        allowed=allowed,
        reason=final_reason,
        matched_policy=matched,
    )
