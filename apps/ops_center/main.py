"""OpsCenter FastAPI service — port 8006."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException

from apps.ops_center import __version__
from apps.ops_center.config import OpsCenterSettings
from apps.ops_center.engine import (
    _auto_seed,
    evaluate_rules,
    get_rule,
    list_firing_alerts,
    list_rules,
    register_rule,
    update_rule_state,
)
from apps.ops_center.models import (
    AlertListResponse,
    AlertRule,
    AlertRuleListResponse,
    AlertState,
    ModelUsageStats,
    OpsHealthResponse,
    TaskStats,
    TenantOverview,
)
from common.tracing import get_logger

log = get_logger("ops_center")

settings = OpsCenterSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _auto_seed()
    log.info("ops_center.started", port=settings.port)
    yield
    log.info("ops_center.stopped")


app = FastAPI(title="OpsCenter", version=__version__, lifespan=lifespan)


@app.get("/ops/health", response_model=OpsHealthResponse)
async def hub_health() -> OpsHealthResponse:
    """Overall OpsCenter health and active alert count."""
    alerts = list_firing_alerts()
    return OpsHealthResponse(
        status="healthy" if not alerts else "degraded",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        active_alerts=len(alerts),
    )


@app.get("/ops/stats/tasks", response_model=TaskStats)
async def task_stats(days: int = 1) -> TaskStats:
    """Return task completion statistics.

    In Phase 1, this returns stub data. Real implementation queries
    the Task table in the database.
    """
    # Trigger rule evaluation on each stats call
    evaluate_rules()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Stub: in production, this would aggregate from the Task table
    return TaskStats(
        period="daily",
        date=today,
        total_tasks=0,
        completed=0,
        failed=0,
        avg_duration_ms=0.0,
        completion_rate=0.0,
        failure_rate=0.0,
    )


@app.get("/ops/stats/model-usage", response_model=list[ModelUsageStats])
async def model_usage_stats(employee_id: Optional[str] = None, days: int = 7) -> list[ModelUsageStats]:
    """Return model usage statistics.

    Pulls aggregated usage from ModelHub's UsageTracker.
    """
    try:
        from apps.model_hub.usage import UsageTracker

        tracker = UsageTracker()  # Shared instance
        if employee_id:
            records = tracker.get_usage(employee_id, days=days)
        else:
            # Return all employees
            records = []
            # Note: in production, this would query all employees

        return [
            ModelUsageStats(
                date=rec.date,
                total_requests=rec.request_count,
                total_tokens=rec.total_tokens,
                prompt_tokens=rec.prompt_tokens,
                completion_tokens=rec.completion_tokens,
                cost_usd=rec.cost_usd,
            )
            for rec in records
        ]
    except ImportError:
        # ModelHub not available yet
        return []


@app.get("/ops/alerts", response_model=AlertListResponse)
async def list_alerts() -> AlertListResponse:
    """Return all currently firing alerts."""
    evaluate_rules()
    alerts = list_firing_alerts()
    return AlertListResponse(alerts=alerts, total=len(alerts))


@app.get("/ops/rules", response_model=AlertRuleListResponse)
async def list_rules_endpoint() -> AlertRuleListResponse:
    """Return all alert rules."""
    rules = list_rules()
    return AlertRuleListResponse(rules=rules, total=len(rules))


@app.post("/ops/rules", response_model=AlertRule, status_code=201)
async def create_rule(rule: AlertRule) -> AlertRule:
    """Register a new alert rule."""
    existing = get_rule(rule.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Rule with id '{rule.id}' already exists")
    register_rule(rule)
    log.info("ops_center.rule.created", rule_id=rule.id)
    return rule


@app.patch("/ops/rules/{rule_id}/state")
async def patch_rule_state(rule_id: str, new_state: AlertState) -> AlertRule:
    """Update the state of an alert rule (active/muted/resolved)."""
    rule = get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return update_rule_state(rule_id, new_state)


@app.get("/ops/tenant/{tenant_id}/overview", response_model=TenantOverview)
async def tenant_overview(tenant_id: str) -> TenantOverview:
    """Return overview stats for a tenant."""
    alerts = list_firing_alerts()
    return TenantOverview(
        tenant_id=tenant_id,
        active_employees=0,
        total_tasks_today=0,
        model_cost_today_usd=0.0,
        active_alerts=len(alerts),
    )
