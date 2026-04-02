"""Approval workflow data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalNodeType(str, Enum):
    """Approval node type."""

    SINGLE = "single"  # One approver must approve
    AND = "and"  # All approvers must approve (会签)
    OR = "or"  # Any approver can approve (或签)


class ApprovalStatus(str, Enum):
    """Status of an approval step."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ApprovalResult(str, Enum):
    """Outcome of an approval decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ConditionOperator(str, Enum):
    """Operators for conditional routing."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NE = "ne"
    IN = "in"
    CONTAINS = "contains"


class ApprovalCondition(BaseModel):
    """A condition for routing to a specific approval path."""

    field: str = Field(description="Attribute to evaluate, e.g. 'amount', 'risk_level'")
    operator: ConditionOperator
    value: Any = Field(description="Threshold value")
    # e.g. {"field": "amount", "operator": "gt", "value": 10000}


class ApprovalStep(BaseModel):
    """A single step in an approval workflow."""

    step_id: str
    name: str
    description: str = ""
    node_type: ApprovalNodeType = ApprovalNodeType.SINGLE
    # Approvers for this step
    approvers: List[str] = Field(default_factory=list)  # user_ids or role names
    # Fallback approver if primary is unavailable
    fallback_approver: Optional[str] = None
    # Time limit in minutes (None = no limit)
    timeout_minutes: Optional[int] = None
    # Escalation to this user/role after timeout
    escalate_to: Optional[str] = None
    # Conditions that must match for this step to be used
    conditions: List[ApprovalCondition] = Field(default_factory=list)
    # Order in the workflow (steps are evaluated in order)
    order: int = 0

    model_config = {"use_enum_values": True, "extra": "ignore"}


class ApprovalWorkflow(BaseModel):
    """Definition of an approval workflow."""

    id: str
    name: str
    description: str = ""
    # Steps ordered by priority
    steps: List[ApprovalStep] = Field(default_factory=list)
    # Default timeout for the entire workflow (minutes)
    default_timeout_minutes: Optional[int] = Field(None, description="Overall timeout in minutes")
    # Auto-cancel if no approval within this time
    auto_cancel_minutes: Optional[int] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"use_enum_values": True, "extra": "ignore"}

    def matching_step(self, attributes: Dict[str, Any]) -> Optional[ApprovalStep]:
        """Find the first step whose conditions match the given attributes."""
        for step in sorted(self.steps, key=lambda s: s.order):
            if self._conditions_match(step, attributes):
                return step
        return None

    def _conditions_match(self, step: ApprovalStep, attrs: Dict[str, Any]) -> bool:
        if not step.conditions:
            return True
        for cond in step.conditions:
            val = attrs.get(cond.field)
            if val is None:
                return False
            op = cond.operator
            if op == ConditionOperator.GT:
                ok = float(val) > float(cond.value)
            elif op == ConditionOperator.GTE:
                ok = float(val) >= float(cond.value)
            elif op == ConditionOperator.LT:
                ok = float(val) < float(cond.value)
            elif op == ConditionOperator.LTE:
                ok = float(val) <= float(cond.value)
            elif op == ConditionOperator.EQ:
                ok = val == cond.value
            elif op == ConditionOperator.NE:
                ok = val != cond.value
            elif op == ConditionOperator.IN:
                ok = val in (cond.value if isinstance(cond.value, list) else [cond.value])
            elif op == ConditionOperator.CONTAINS:
                ok = str(cond.value) in str(val)
            else:
                ok = False
            if not ok:
                return False
        return True


class ApprovalRequest(BaseModel):
    """An active approval request instance."""

    request_id: str
    workflow_id: str
    # Who initiated the request
    requester_id: str
    tenant_id: str
    # What action/resource is being approved
    resource_type: str  # e.g. "task", "payment", "deletion"
    resource_id: str
    resource_summary: str = ""
    # Context attributes for conditional routing
    attributes: Dict[str, Any] = Field(default_factory=dict)
    # The step currently active
    current_step_id: Optional[str] = None
    # Status of each step
    step_statuses: Dict[str, ApprovalStatus] = Field(default_factory=dict)
    # Who approved/rejected
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    # Overall status
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # When the current step was activated
    step_started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"use_enum_values": True, "extra": "ignore"}

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class ApprovalDecisionRequest(BaseModel):
    """Request to approve or reject an approval."""

    request_id: str
    decision: ApprovalResult
    comment: str = ""
    approver_id: str


class ApprovalResponse(BaseModel):
    """Response for an approval action."""

    request_id: str
    decision: ApprovalResult
    decided_by: str
    comment: str = ""
    next_step_id: Optional[str] = None
    is_final: bool = False
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


class ApprovalListResponse(BaseModel):
    """List approval requests."""

    requests: List[ApprovalRequest]
    total: int


class ApprovalSubmitRequest(BaseModel):
    """Submit an approval request."""

    workflow_id: str
    requester_id: str
    tenant_id: str
    resource_type: str
    resource_id: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    resource_summary: str = ""

    model_config = {"extra": "ignore"}
