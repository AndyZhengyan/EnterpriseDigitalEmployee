"""RBAC — Role-Based Access Control engine.

Provides:
- Built-in role definitions with permission hierarchies
- In-memory role assignments (user_id → role)
- Permission evaluation with inheritance
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set

from apps.governance.errors import GovernanceError, GovernanceErrorCode
from apps.governance.models import Permission, Role, RoleDefinition, UserRole
from common.tracing import get_logger

log = get_logger("governance.rbac")

# ============== Built-in Role Definitions ==============

_BUILTIN_ROLE_DEFINITIONS: Dict[Role, RoleDefinition] = {
    Role.PLATFORM_ADMIN: RoleDefinition(
        role=Role.PLATFORM_ADMIN,
        description="Platform-wide administrator — full access",
        permissions=[Permission.READ, Permission.WRITE, Permission.ADMIN],
        inherits_from=[],
        max_scope="platform",
    ),
    Role.TENANT_ADMIN: RoleDefinition(
        role=Role.TENANT_ADMIN,
        description="Tenant administrator — full access within tenant",
        permissions=[Permission.READ, Permission.WRITE, Permission.ADMIN],
        inherits_from=[Role.TENANT_OPERATOR],
        max_scope="tenant",
    ),
    Role.TENANT_OPERATOR: RoleDefinition(
        role=Role.TENANT_OPERATOR,
        description="Tenant operator — manage employees and view analytics",
        permissions=[Permission.READ, Permission.WRITE],
        inherits_from=[Role.EMPLOYEE_USER],
        max_scope="tenant",
    ),
    Role.EMPLOYEE_USER: RoleDefinition(
        role=Role.EMPLOYEE_USER,
        description="Basic employee — read and execute tasks",
        permissions=[Permission.READ],
        inherits_from=[],
        max_scope="self",
    ),
}

# Global state
_role_definitions: Dict[Role, RoleDefinition] = {}
_user_roles: Dict[str, UserRole] = {}  # key: f"{tenant_id}:{user_id}"
_lock = threading.Lock()


def _auto_seed() -> None:
    """Register built-in role definitions."""
    global _role_definitions
    with _lock:
        _role_definitions = dict(_BUILTIN_ROLE_DEFINITIONS)


def _effective_permissions(role: Role) -> Set[Permission]:
    """Compute the full permission set for a role, including inherited."""
    with _lock:
        defn = _role_definitions.get(role)
    if defn is None:
        return set()

    result: Set[Permission] = set(defn.permissions)
    for inherited_role in defn.inherits_from:
        result |= _effective_permissions(inherited_role)
    return result


def has_permission(user_id: str, permission: Permission, tenant_id: str) -> bool:
    """Check if a user has a specific permission (within their scope)."""
    key = f"{tenant_id}:{user_id}"
    with _lock:
        assignment = _user_roles.get(key)

    if assignment is None:
        return False

    # Platform admin has all permissions regardless of tenant
    if assignment.role == Role.PLATFORM_ADMIN:
        return True

    # Check tenant boundary: tenant_admin/operator/user can only act within their tenant
    if assignment.tenant_id != tenant_id:
        return False

    effective = _effective_permissions(assignment.role)
    return permission in effective


def assign_role(user_id: str, role: Role, tenant_id: str, assigned_by: str) -> UserRole:
    """Assign a role to a user within a tenant."""
    key = f"{tenant_id}:{user_id}"
    with _lock:
        if key in _user_roles:
            raise GovernanceError(
                f"User '{user_id}' already has a role in tenant '{tenant_id}'",
                code=GovernanceErrorCode.USER_ALREADY_ASSIGNED.value[0],
            )
        assignment = UserRole(
            user_id=user_id,
            role=role,
            tenant_id=tenant_id,
            assigned_by=assigned_by,
        )
        _user_roles[key] = assignment
    role_str = role.value if isinstance(role, Role) else str(role)
    log.info("rbac.role.assigned", user_id=user_id, role=role_str, tenant_id=tenant_id)
    return assignment


def revoke_role(user_id: str, tenant_id: str) -> bool:
    """Revoke a user's role in a tenant."""
    key = f"{tenant_id}:{user_id}"
    with _lock:
        if key in _user_roles:
            del _user_roles[key]
            return True
        return False


def get_user_role(user_id: str, tenant_id: str) -> Optional[UserRole]:
    """Get a user's role assignment in a tenant."""
    key = f"{tenant_id}:{user_id}"
    with _lock:
        return _user_roles.get(key)


def list_roles() -> List[RoleDefinition]:
    """List all registered role definitions."""
    with _lock:
        return list(_role_definitions.values())


def list_user_roles() -> List[UserRole]:
    """List all user-role assignments."""
    with _lock:
        return list(_user_roles.values())
