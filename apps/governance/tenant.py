"""Tenant registry, status, plans, and quota management."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class TenantPlan(str, Enum):
    """Tenant subscription plan."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Default quotas per plan
_PLAN_DEFAULTS: Dict[TenantPlan, Dict[str, int]] = {
    TenantPlan.FREE: {
        "max_users": 5,
        "max_api_calls_per_day": 1000,
        "max_storage_mb": 100,
        "max_concurrent_tasks": 2,
    },
    TenantPlan.PRO: {
        "max_users": 50,
        "max_api_calls_per_day": 50000,
        "max_storage_mb": 5000,
        "max_concurrent_tasks": 20,
    },
    TenantPlan.ENTERPRISE: {
        "max_users": -1,  # unlimited
        "max_api_calls_per_day": -1,
        "max_storage_mb": -1,
        "max_concurrent_tasks": -1,
    },
}


class TenantQuota(BaseModel):
    """Resource quotas for a tenant."""

    max_users: int = -1
    max_api_calls_per_day: int = -1
    max_storage_mb: int = -1
    max_concurrent_tasks: int = -1

    model_config = {"extra": "ignore"}

    def is_unlimited(self, key: str) -> bool:
        return getattr(self, key, -1) == -1


class Tenant(BaseModel):
    """Tenant entity."""

    id: str
    name: str
    plan: TenantPlan = TenantPlan.FREE
    status: TenantStatus = TenantStatus.ACTIVE
    quota: TenantQuota = Field(default_factory=lambda: TenantQuota())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    suspended_at: Optional[datetime] = None

    model_config = {"use_enum_values": True, "extra": "ignore"}

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE


class TenantUsage(BaseModel):
    """Current usage counters for a tenant."""

    tenant_id: str
    user_count: int = 0
    api_calls_today: int = 0
    storage_mb: float = 0.0
    concurrent_tasks: int = 0
    last_reset_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


# ============== Global Store ==============

_tenants: Dict[str, Tenant] = {}
_usage: Dict[str, TenantUsage] = {}
_lock = threading.Lock()


def _auto_seed() -> None:
    """Seed the store with a default platform tenant."""
    global _tenants
    with _lock:
        if "platform" not in _tenants:
            _tenants["platform"] = Tenant(
                id="platform",
                name="Platform",
                plan=TenantPlan.ENTERPRISE,
                status=TenantStatus.ACTIVE,
                quota=TenantQuota(**_PLAN_DEFAULTS[TenantPlan.ENTERPRISE]),
            )
            _usage["platform"] = TenantUsage(tenant_id="platform")


# ============== CRUD ==============


def register_tenant(
    name: str,
    plan: TenantPlan = TenantPlan.FREE,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tenant:
    """Register a new tenant. Returns the created tenant."""
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    quota = TenantQuota(**_PLAN_DEFAULTS[plan])
    tenant = Tenant(
        id=tenant_id,
        name=name,
        plan=plan,
        status=TenantStatus.ACTIVE,
        quota=quota,
        metadata=metadata or {},
    )
    with _lock:
        _tenants[tenant_id] = tenant
        _usage[tenant_id] = TenantUsage(tenant_id=tenant_id)
    return tenant


def get_tenant(tenant_id: str) -> Optional[Tenant]:
    """Get a tenant by ID."""
    with _lock:
        return _tenants.get(tenant_id)


def list_tenants(status: Optional[TenantStatus] = None) -> List[Tenant]:
    """List all tenants, optionally filtered by status."""
    with _lock:
        result = list(_tenants.values())
    if status:
        result = [t for t in result if t.status == status]
    return result


def update_tenant(tenant_id: str, **fields: Any) -> Optional[Tenant]:
    """Update tenant fields. Returns updated tenant or None."""
    with _lock:
        tenant = _tenants.get(tenant_id)
        if tenant is None:
            return None
        for key, value in fields.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        tenant.updated_at = datetime.now(timezone.utc)
        _tenants[tenant_id] = tenant
        return tenant


def suspend_tenant(tenant_id: str) -> bool:
    """Suspend a tenant. Returns True if found and suspended."""
    with _lock:
        tenant = _tenants.get(tenant_id)
        if tenant is None:
            return False
        tenant.status = TenantStatus.SUSPENDED
        tenant.suspended_at = datetime.now(timezone.utc)
        tenant.updated_at = datetime.now(timezone.utc)
        _tenants[tenant_id] = tenant
    return True


def delete_tenant(tenant_id: str) -> bool:
    """Soft-delete a tenant. Returns True if found and deleted."""
    return update_tenant(tenant_id, status=TenantStatus.DELETED) is not None


# ============== Quota Management ==============


def get_quota(tenant_id: str) -> Optional[TenantQuota]:
    """Get a tenant's quota."""
    tenant = get_tenant(tenant_id)
    return tenant.quota if tenant else None


def update_quota(tenant_id: str, **quota_fields: Any) -> Optional[TenantQuota]:
    """Update a tenant's quota fields. Returns updated quota or None."""
    with _lock:
        tenant = _tenants.get(tenant_id)
        if tenant is None:
            return None
        for key, value in quota_fields.items():
            if hasattr(tenant.quota, key):
                setattr(tenant.quota, key, value)
        tenant.updated_at = datetime.now(timezone.utc)
        _tenants[tenant_id] = tenant
        return tenant.quota


def get_usage(tenant_id: str) -> Optional[TenantUsage]:
    """Get current usage for a tenant."""
    with _lock:
        return _usage.get(tenant_id)


def increment_api_calls(tenant_id: str) -> int:
    """Increment daily API call counter. Returns new count."""
    with _lock:
        usage = _usage.get(tenant_id)
        if usage is None:
            usage = TenantUsage(tenant_id=tenant_id)
            _usage[tenant_id] = usage
        usage.api_calls_today += 1
        return usage.api_calls_today


def check_quota(tenant_id: str) -> tuple[bool, Optional[str]]:
    """Check if tenant is within quota limits. Returns (ok, reason)."""
    tenant = get_tenant(tenant_id)
    if tenant is None:
        return False, "Tenant not found"
    if not tenant.is_active():
        return False, f"Tenant is {tenant.status}"

    usage = get_usage(tenant_id)
    if usage is None:
        return True, ""

    quota = tenant.quota
    if not quota.is_unlimited("max_api_calls_per_day"):
        if usage.api_calls_today >= quota.max_api_calls_per_day:
            return False, "Daily API call quota exceeded"
    if not quota.is_unlimited("max_concurrent_tasks"):
        if usage.concurrent_tasks >= quota.max_concurrent_tasks:
            return False, "Concurrent task quota exceeded"

    return True, ""


def set_usage(tenant_id: str, **fields: Any) -> Optional[TenantUsage]:
    """Set usage fields for a tenant. Returns updated usage or None."""
    with _lock:
        usage = _usage.get(tenant_id)
        if usage is None:
            return None
        for key, value in fields.items():
            if hasattr(usage, key):
                setattr(usage, key, value)
        _usage[tenant_id] = usage
        return usage
