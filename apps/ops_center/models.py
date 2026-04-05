"""OpsCenter request/response models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity level."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """Alert rule state."""

    ACTIVE = "active"
    FIRING = "firing"
    RESOLVED = "resolved"
    MUTED = "muted"


class AlertRule(BaseModel):
    """An alerting rule definition."""

    id: str
    name: str
    description: str = ""
    metric: str  # e.g. "task_failure_rate", "model_token_usage"
    condition: str  # e.g. "> 0.1", ">= 10000"
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    state: AlertState = AlertState.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


class Alert(BaseModel):
    """A triggered alert instance."""

    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}


class TaskStats(BaseModel):
    """Aggregated task statistics."""

    period: str = "daily"  # daily | weekly | monthly
    date: str = ""  # YYYY-MM-DD
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    completion_rate: float = 0.0
    failure_rate: float = 0.0


class ModelUsageStats(BaseModel):
    """Aggregated model usage statistics."""

    date: str = ""  # YYYY-MM-DD
    total_requests: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


class TenantOverview(BaseModel):
    """Overview stats for a tenant."""

    tenant_id: str
    active_employees: int = 0
    total_tasks_today: int = 0
    model_cost_today_usd: float = 0.0
    active_alerts: int = 0


class AlertListResponse(BaseModel):
    """Response for GET /ops/alerts."""

    alerts: List[Alert]
    total: int


class AlertRuleListResponse(BaseModel):
    """Response for GET /ops/rules."""

    rules: List[AlertRule]
    total: int


class OpsHealthResponse(BaseModel):
    """Response for GET /ops/health."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_alerts: int = 0
    document_count: int = 0

    model_config = {"extra": "ignore"}
