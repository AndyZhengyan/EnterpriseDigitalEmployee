"""Governance request/response models — RBAC/ABAC."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============== Enums ==============


class Role(str, Enum):
    """Platform-wide roles (most permissive to least)."""

    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_OPERATOR = "tenant_operator"
    EMPLOYEE_USER = "employee_user"


class Permission(str, Enum):
    """Granular permissions."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class ABACAttribute(str, Enum):
    """ABAC attribute categories."""

    DEPARTMENT = "department"
    POSITION = "position"
    TASK_TYPE = "task_type"
    RESOURCE_OWNER = "resource_owner"
    TENANT_ID = "tenant_id"
    EMPLOYEE_ID = "employee_id"
    RISK_LEVEL = "risk_level"


class ABACAction(str, Enum):
    """Actions for ABAC policy evaluation."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"


class ABACEffect(str, Enum):
    """ABAC policy effect."""

    ALLOW = "allow"
    DENY = "deny"


# ============== Core Models ==============


class RoleDefinition(BaseModel):
    """Definition of a role with its permissions and scope."""

    role: Role
    description: str = ""
    permissions: List[Permission] = Field(default_factory=list)
    # Hierarchy: higher roles inherit lower roles' permissions
    inherits_from: List[Role] = Field(default_factory=list)
    max_scope: str = "tenant"  # "platform" | "tenant" | "self"

    model_config = {"use_enum_values": True, "extra": "ignore"}


class UserRole(BaseModel):
    """A user-to-role assignment."""

    user_id: str
    role: Role
    tenant_id: str
    assigned_by: str
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"use_enum_values": True, "extra": "ignore"}


class ABACPolicy(BaseModel):
    """An ABAC policy: attributes → effect."""

    id: str
    name: str
    description: str = ""
    # Conditions that must all match
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Attribute conditions, e.g. {'department': 'engineering', 'risk_level': 'low'}",
    )
    # Actions this policy applies to
    actions: List[ABACAction] = Field(default_factory=list)
    # Resources this policy applies to (glob pattern)
    resources: List[str] = Field(default_factory=list)
    effect: ABACEffect = ABACEffect.DENY
    priority: int = Field(0, description="Higher priority policies are evaluated first")
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"use_enum_values": True, "extra": "ignore"}


# ============== Request/Response Models ==============


class AuthContext(BaseModel):
    """Auth context extracted from JWT token."""

    user_id: str
    tenant_id: str
    role: Role
    attributes: Dict[str, Any] = Field(default_factory=dict)
    exp: Optional[int] = None

    model_config = {"use_enum_values": True, "extra": "ignore"}


class RoleAssignRequest(BaseModel):
    """Assign a role to a user."""

    user_id: str
    role: Role
    tenant_id: str

    model_config = {"use_enum_values": True}


class RoleListResponse(BaseModel):
    """List all role definitions."""

    roles: List[RoleDefinition]
    total: int


class UserRoleListResponse(BaseModel):
    """List all user-role assignments."""

    assignments: List[UserRole]
    total: int


class PolicyCreateRequest(BaseModel):
    """Create a new ABAC policy."""

    id: str
    name: str
    description: str = ""
    conditions: Dict[str, Any] = {}
    actions: List[ABACAction]
    resources: List[str] = Field(default_factory=list)
    effect: ABACEffect = ABACEffect.DENY
    priority: int = 0
    enabled: bool = True

    model_config = {"use_enum_values": True}


class PolicyListResponse(BaseModel):
    """List all ABAC policies."""

    policies: List[ABACPolicy]
    total: int


class PermissionCheckRequest(BaseModel):
    """Check if a user has permission for an action."""

    user_id: str
    action: str
    resource: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class PermissionCheckResponse(BaseModel):
    """Result of a permission check."""

    allowed: bool
    reason: str = ""
    matched_policy: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response."""

    token: str
    expires_in: int
    token_type: str = "Bearer"


class GovernanceHealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    role_count: int = 0
    policy_count: int = 0

    model_config = {"extra": "ignore"}
