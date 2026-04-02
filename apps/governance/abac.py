"""ABAC — Attribute-Based Access Control policy engine.

Evaluates dynamic access policies based on subject attributes, resource
attributes, and environmental context.
"""

from __future__ import annotations

import fnmatch
import threading
from typing import Any, Dict, List, Optional

from apps.governance.models import (
    ABACAction,
    ABACEffect,
    ABACPolicy,
    Role,
    UserRole,
)
from common.tracing import get_logger

log = get_logger("governance.abac")

# Global policy store
_policies: Dict[str, ABACPolicy] = {}
_lock = threading.Lock()

# ============== Built-in Policies ==============

_BUILTIN_POLICIES: List[ABACPolicy] = [
    ABACPolicy(
        id="deny-all-platform-admin-write",
        name="Deny platform admin write actions (platform admins use read-only by default)",
        conditions={"role": "platform_admin"},
        actions=[ABACAction.READ],
        resources=["*"],
        effect=ABACEffect.ALLOW,
        priority=100,
        enabled=False,  # Disabled: platform_admin should have full access
    ),
    ABACPolicy(
        id="allow-employee-low-risk-tasks",
        name="Allow employee users to execute low-risk tasks",
        conditions={"risk_level": "low"},
        actions=[ABACAction.EXECUTE],
        resources=["task:*"],
        effect=ABACEffect.ALLOW,
        priority=50,
    ),
    ABACPolicy(
        id="deny-employee-high-risk-tasks",
        name="Deny employee users from high-risk task execution",
        conditions={"risk_level": "high"},
        actions=[ABACAction.EXECUTE],
        resources=["task:*"],
        effect=ABACEffect.DENY,
        priority=80,
    ),
    ABACPolicy(
        id="allow-tenant-admin-all-tenant-resources",
        name="Allow tenant admins full access within their tenant",
        conditions={"role": "tenant_admin"},
        actions=[ABACAction.CREATE, ABACAction.READ, ABACAction.UPDATE, ABACAction.DELETE, ABACAction.EXECUTE],
        resources=["tenant:*"],
        effect=ABACEffect.ALLOW,
        priority=70,
    ),
]


def _auto_seed() -> None:
    """Register built-in ABAC policies."""
    global _policies
    with _lock:
        for policy in _BUILTIN_POLICIES:
            _policies[policy.id] = policy


def register_policy(policy: ABACPolicy) -> None:
    """Register or update an ABAC policy."""
    with _lock:
        _policies[policy.id] = policy
    log.info("abac.policy.registered", policy_id=policy.id, effect=policy.effect.value)


def get_policy(policy_id: str) -> Optional[ABACPolicy]:
    with _lock:
        return _policies.get(policy_id)


def list_policies() -> List[ABACPolicy]:
    with _lock:
        return list(sorted(_policies.values(), key=lambda p: p.priority, reverse=True))


def _match_resource(resource: str, pattern: str) -> bool:
    """Check if a resource matches a glob pattern."""
    return fnmatch.fnmatch(resource, pattern)


def _match_condition(attr_value: Any, cond_value: Any) -> bool:
    """Check if an attribute value matches a condition value."""
    if isinstance(cond_value, list):
        return attr_value in cond_value
    if isinstance(cond_value, str) and "*" in cond_value:
        return fnmatch.fnmatch(str(attr_value), cond_value)
    return attr_value == cond_value


def _evaluate_conditions(conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Check if all conditions in a policy match the evaluation context."""
    if not conditions:
        return True
    for key, cond_value in conditions.items():
        # Attribute can be nested: e.g. "user.department"
        attr_value = context.get(key)
        if attr_value is None:
            # Try without prefix
            for ctx_key, ctx_val in context.items():
                if ctx_key.endswith(key):
                    attr_value = ctx_val
                    break
        if not _match_condition(attr_value, cond_value):
            return False
    return True


def evaluate(
    action: str,
    resource: str,
    user_role: Optional[UserRole],
    attributes: Dict[str, Any],
) -> tuple[bool, str, Optional[str]]:
    """Evaluate ABAC policies and return (allowed, reason, matched_policy_id).

    Policies are evaluated in priority order (highest first).
    First matching policy wins. If no policy matches, default deny.
    """
    # Build evaluation context from user attributes
    context: Dict[str, Any] = dict(attributes)
    if user_role:
        context["role"] = user_role.role.value if isinstance(user_role.role, Role) else user_role.role
        context["tenant_id"] = user_role.tenant_id
        context["user_id"] = user_role.user_id

    policies = list_policies()

    for policy in policies:
        if not policy.enabled:
            continue

        # Check if policy applies to this action
        try:
            abac_action = ABACAction(action)
        except ValueError:
            abac_action = ABACAction.READ

        if policy.actions and abac_action not in policy.actions:
            continue

        # Check resource match
        if policy.resources and not any(_match_resource(resource, r) for r in policy.resources):
            continue

        # Check conditions
        if not _evaluate_conditions(policy.conditions, context):
            continue

        # Policy matches
        if policy.effect == ABACEffect.ALLOW:
            return True, f"Allowed by policy '{policy.name}'", policy.id
        else:
            return False, f"Denied by policy '{policy.name}'", policy.id

    # No matching policy: default deny
    return False, "No matching ABAC policy found", None


class ABACEvaluator:
    """Reusable ABAC evaluator bound to a specific user context."""

    def __init__(self, user_role: Optional[UserRole], base_attributes: Optional[Dict[str, Any]] = None) -> None:
        self.user_role = user_role
        self.base_attributes = base_attributes or {}

    def check(self, action: str, resource: str, **attrs: Any) -> tuple[bool, str, Optional[str]]:
        """Evaluate an action on a resource with additional attributes."""
        context = {**self.base_attributes, **attrs}
        return evaluate(action, resource, self.user_role, context)
