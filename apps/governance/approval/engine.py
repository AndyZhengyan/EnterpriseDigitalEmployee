"""Approval workflow engine — routing, state machine, timeout escalation."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from apps.governance.approval.models import (
    ApprovalCondition,
    ApprovalDecisionRequest,
    ApprovalNodeType,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalResult,
    ApprovalStatus,
    ApprovalStep,
    ApprovalWorkflow,
    ConditionOperator,
)
from common.tracing import get_logger

log = get_logger("governance.approval")

# Global stores
_workflows: Dict[str, ApprovalWorkflow] = {}
_requests: Dict[str, ApprovalRequest] = {}
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ============== Built-in Workflows ==============

_BUILTIN_WORKFLOWS: List[ApprovalWorkflow] = [
    ApprovalWorkflow(
        id="high-risk-task",
        name="High Risk Task Approval",
        description="Require approval for high-risk operations",
        steps=[
            ApprovalStep(
                step_id="supervisor-approval",
                name="Supervisor Approval",
                description="Direct supervisor must approve high-risk tasks",
                node_type=ApprovalNodeType.SINGLE,
                approvers=["supervisor"],
                timeout_minutes=60,
                escalate_to="manager",
                order=1,
                conditions=[
                    ApprovalCondition(field="risk_level", operator=ConditionOperator.EQ, value="high"),
                ],
            ),
        ],
        default_timeout_minutes=None,
        enabled=True,
    ),
    ApprovalWorkflow(
        id="deletion-approval",
        name="Deletion Operation Approval",
        description="Require dual approval for deletion operations",
        steps=[
            ApprovalStep(
                step_id="manager-sign-off",
                name="Manager Sign-off",
                description="Manager must sign off on deletion",
                node_type=ApprovalNodeType.AND,
                approvers=["manager"],
                timeout_minutes=120,
                escalate_to="platform_admin",
                order=1,
                conditions=[
                    ApprovalCondition(field="operation_type", operator=ConditionOperator.EQ, value="deletion"),
                ],
            ),
        ],
        default_timeout_minutes=None,
        enabled=True,
    ),
]


def _auto_seed() -> None:
    """Register built-in approval workflows."""
    global _workflows
    with _lock:
        for wf in _BUILTIN_WORKFLOWS:
            _workflows[wf.id] = wf


def register_workflow(workflow: ApprovalWorkflow) -> None:
    with _lock:
        _workflows[workflow.id] = workflow
    log.info("approval.workflow.registered", workflow_id=workflow.id, steps=len(workflow.steps))


def get_workflow(workflow_id: str) -> Optional[ApprovalWorkflow]:
    with _lock:
        return _workflows.get(workflow_id)


def list_workflows() -> List[ApprovalWorkflow]:
    with _lock:
        return [wf for wf in _workflows.values() if wf.enabled]


def _start_step(req: ApprovalRequest, step_id: str, workflow: ApprovalWorkflow) -> None:
    """Activate a specific step in the approval workflow."""
    step = next((s for s in workflow.steps if s.step_id == step_id), None)
    if step is None:
        return

    req.current_step_id = step_id
    req.step_statuses[step_id] = ApprovalStatus.PENDING
    req.step_started_at = _now()

    if step.timeout_minutes:
        req.expires_at = _now() + timedelta(minutes=step.timeout_minutes)
    else:
        req.expires_at = None

    req.updated_at = _now()
    log.info(
        "approval.step.started",
        request_id=req.request_id,
        step_id=step_id,
        approvers=step.approvers,
        timeout_minutes=step.timeout_minutes,
    )


def _complete_step(req: ApprovalRequest, workflow: ApprovalWorkflow) -> Optional[str]:
    """Complete the current step. Returns next step_id or None if final."""
    if req.current_step_id is None:
        return None

    current_status = req.step_statuses.get(req.current_step_id, ApprovalStatus.PENDING)

    # If current step is pending (no decision yet), skip it and move to next
    if current_status == ApprovalStatus.PENDING:
        req.step_statuses[req.current_step_id] = ApprovalStatus.SKIPPED

    # Find next step
    current_order = next((s.order for s in workflow.steps if s.step_id == req.current_step_id), 0)
    next_step = next(
        (s for s in sorted(workflow.steps, key=lambda x: x.order) if s.order > current_order),
        None,
    )

    if next_step:
        _start_step(req, next_step.step_id, workflow)
        return next_step.step_id
    else:
        return None


def submit_approval_request(
    workflow_id: str,
    requester_id: str,
    tenant_id: str,
    resource_type: str,
    resource_id: str,
    attributes: Dict[str, Any],
    resource_summary: str = "",
) -> Optional[ApprovalRequest]:
    """Submit a new approval request. Returns None if no matching workflow step found."""
    workflow = get_workflow(workflow_id)
    if workflow is None or not workflow.enabled:
        log.warning("approval.workflow.not_found", workflow_id=workflow_id)
        return None

    # Find matching step based on attributes
    matching_step = workflow.matching_step(attributes)
    if matching_step is None:
        # No conditions match — no approval needed
        log.info("approval.no_step_matched", workflow_id=workflow_id, attributes=attributes)
        return None

    request = ApprovalRequest(
        request_id=f"apr-{uuid.uuid4().hex[:8]}",
        workflow_id=workflow_id,
        requester_id=requester_id,
        tenant_id=tenant_id,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_summary=resource_summary,
        attributes=attributes,
        current_step_id=None,
        step_statuses={},
        decisions=[],
        status=ApprovalStatus.PENDING,
    )

    with _lock:
        _requests[request.request_id] = request

    # Start the first matching step
    _start_step(request, matching_step.step_id, workflow)
    request.status = ApprovalStatus.PENDING

    log.info(
        "approval.request.submitted",
        request_id=request.request_id,
        workflow_id=workflow_id,
        step_id=matching_step.step_id,
    )
    return request


def get_request(request_id: str) -> Optional[ApprovalRequest]:
    with _lock:
        return _requests.get(request_id)


def list_requests(
    status: Optional[ApprovalStatus] = None,
    requester_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> List[ApprovalRequest]:
    with _lock:
        results = list(_requests.values())
    if status:
        results = [r for r in results if r.status == status]
    if requester_id:
        results = [r for r in results if r.requester_id == requester_id]
    if tenant_id:
        results = [r for r in results if r.tenant_id == tenant_id]
    return results


def process_decision(decision: ApprovalDecisionRequest) -> ApprovalResponse:
    """Process an approval or rejection decision."""
    request = get_request(decision.request_id)
    if request is None:
        raise ValueError(f"Approval request not found: {decision.request_id}")

    workflow = get_workflow(request.workflow_id)
    if workflow is None:
        raise ValueError(f"Workflow not found: {request.workflow_id}")

    current_step_id = request.current_step_id
    if current_step_id is None:
        raise ValueError(f"No active step for request: {decision.request_id}")

    step = next((s for s in workflow.steps if s.step_id == current_step_id), None)
    if step is None:
        raise ValueError(f"Step not found: {current_step_id}")

    # Record decision
    request.decisions.append(
        {
            "step_id": current_step_id,
            "approver_id": decision.approver_id,
            "decision": decision.decision,
            "comment": decision.comment,
            "decided_at": _now().isoformat(),
        }
    )

    # Process based on node type and decision
    if step.node_type == ApprovalNodeType.SINGLE:
        # Single approver: any decision completes the step
        if decision.decision == ApprovalResult.APPROVED:
            request.step_statuses[current_step_id] = ApprovalStatus.APPROVED
        else:
            request.step_statuses[current_step_id] = ApprovalStatus.REJECTED

    elif step.node_type == ApprovalNodeType.AND:
        # AND (会签): wait for ALL approvers
        approved_count = sum(
            1 for d in request.decisions if d["step_id"] == current_step_id and d["decision"] == ApprovalResult.APPROVED
        )
        rejected_count = sum(
            1 for d in request.decisions if d["step_id"] == current_step_id and d["decision"] == ApprovalResult.REJECTED
        )

        if rejected_count > 0:
            request.step_statuses[current_step_id] = ApprovalStatus.REJECTED
        elif approved_count >= len(step.approvers):
            request.step_statuses[current_step_id] = ApprovalStatus.APPROVED
        # Otherwise still pending

    elif step.node_type == ApprovalNodeType.OR:
        # OR (或签): any approval/rejection completes
        if decision.decision == ApprovalResult.APPROVED:
            request.step_statuses[current_step_id] = ApprovalStatus.APPROVED
        else:
            request.step_statuses[current_step_id] = ApprovalStatus.REJECTED

    # Determine overall status
    current_step_status = request.step_statuses.get(current_step_id, ApprovalStatus.PENDING)
    is_step_complete = current_step_status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)

    if not is_step_complete:
        # Step still pending (e.g., AND requiring more approvals)
        request.updated_at = _now()
        with _lock:
            _requests[request.request_id] = request
        return ApprovalResponse(
            request_id=request.request_id,
            decision=decision.decision,
            decided_by=decision.approver_id,
            comment=decision.comment,
            next_step_id=None,
            is_final=False,
        )

    # Step complete — check if approved
    if current_step_status == ApprovalStatus.APPROVED:
        next_step_id = _complete_step(request, workflow)
        if next_step_id is None:
            # Final approval
            request.status = ApprovalStatus.APPROVED
            request.current_step_id = None
            log.info("approval.approved", request_id=request.request_id)
        else:
            request.status = ApprovalStatus.PENDING
            log.info("approval.step.approved.advancing", request_id=request.request_id, next_step_id=next_step_id)
    else:
        # Rejected — fail the whole workflow
        request.status = ApprovalStatus.REJECTED
        request.current_step_id = None
        log.info("approval.rejected", request_id=request.request_id, rejected_by=decision.approver_id)

    request.updated_at = _now()
    with _lock:
        _requests[request.request_id] = request

    return ApprovalResponse(
        request_id=request.request_id,
        decision=decision.decision,
        decided_by=decision.approver_id,
        comment=decision.comment,
        next_step_id=request.current_step_id,
        is_final=request.current_step_id is None,
    )


def check_timeouts() -> List[ApprovalRequest]:
    """Check for expired approval requests and escalate them. Returns escalated requests."""
    escalated = []
    with _lock:
        pending = [r for r in _requests.values() if r.status == ApprovalStatus.PENDING and r.is_expired()]

    for req in pending:
        workflow = get_workflow(req.workflow_id)
        if workflow is None or req.current_step_id is None:
            continue

        step = next((s for s in workflow.steps if s.step_id == req.current_step_id), None)
        if step is None:
            continue

        req.step_statuses[req.current_step_id] = ApprovalStatus.ESCALATED

        if step.escalate_to:
            # Escalate to fallback approver — start a new step
            escalation_step_id = f"{req.current_step_id}-escalated"
            _start_step(req, escalation_step_id, workflow)
            log.warning(
                "approval.escalated",
                request_id=req.request_id,
                from_step=step.step_id,
                escalate_to=step.escalate_to,
            )
        else:
            req.status = ApprovalStatus.ESCALATED
            req.current_step_id = None
            log.warning("approval.timeout", request_id=req.request_id, step_id=step.step_id)

        req.updated_at = _now()
        escalated.append(req)

    with _lock:
        for req in escalated:
            _requests[req.request_id] = req

    return escalated
