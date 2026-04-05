"""OpsCenter alert engine — rule evaluation and alert firing."""

from __future__ import annotations

import operator
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from apps.ops_center.models import Alert, AlertRule, AlertSeverity, AlertState
from common.tracing import get_logger

log = get_logger("ops_center.engine")

# Global alert state
_active_rules: Dict[str, AlertRule] = {}
_firing_alerts: Dict[str, Alert] = {}
_lock = threading.Lock()

# Built-in rules
_BUILTIN_RULES = [
    AlertRule(
        id="high-failure-rate",
        name="High Task Failure Rate",
        description="Triggers when task failure rate exceeds 20%",
        metric="task_failure_rate",
        condition=">=",
        threshold=0.20,
        severity=AlertSeverity.ERROR,
    ),
    AlertRule(
        id="model-quota-warning",
        name="Model Token Quota Warning",
        description="Triggers when daily token usage exceeds 80% of quota",
        metric="model_token_usage",
        condition=">=",
        threshold=0.80,
        severity=AlertSeverity.WARNING,
    ),
    AlertRule(
        id="task-backlog",
        name="Task Backlog Buildup",
        description="Triggers when queued tasks exceed 100",
        metric="task_queue_depth",
        condition=">",
        threshold=100,
        severity=AlertSeverity.WARNING,
    ),
]


def _ops() -> Dict[str, float]:
    """Return current operational metrics (stub — real impl queries hubs)."""
    return {
        "task_failure_rate": 0.05,
        "task_queue_depth": 12,
        "model_token_usage": 0.45,
    }


def _eval_condition(value: float, condition: str, threshold: float) -> bool:
    """Evaluate a simple condition."""
    ops_map = {
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
        "==": operator.eq,
        "!=": operator.ne,
    }
    op = ops_map.get(condition.strip())
    if op is None:
        return False
    return op(value, threshold)


def register_rule(rule: AlertRule) -> None:
    """Register an alert rule."""
    with _lock:
        _active_rules[rule.id] = rule
    log.info("alert.rule.registered", rule_id=rule.id, name=rule.name)


def list_rules() -> List[AlertRule]:
    """Return all alert rules."""
    with _lock:
        return list(_active_rules.values())


def evaluate_rules() -> List[Alert]:
    """Evaluate all rules and return any new firing alerts."""
    metrics = _ops()
    new_alerts: List[Alert] = []

    with _lock:
        for rule in list(_active_rules.values()):
            if rule.state != AlertState.ACTIVE:
                continue

            value = metrics.get(rule.metric, 0.0)
            if _eval_condition(value, rule.condition, rule.threshold):
                if rule.id not in _firing_alerts:
                    alert = Alert(
                        id=str(uuid.uuid4())[:8],
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.name}: {rule.metric}={value:.3f} ({rule.condition} {rule.threshold})",
                        fired_at=datetime.now(timezone.utc),
                    )
                    _firing_alerts[rule.id] = alert
                    new_alerts.append(alert)
                    log.warning("alert.fired", rule_id=rule.id, metric=rule.metric, value=value)
            else:
                # Resolve if it was firing
                if rule.id in _firing_alerts:
                    alert = _firing_alerts.pop(rule.id)
                    alert.resolved_at = datetime.now(timezone.utc)
                    log.info("alert.resolved", rule_id=rule.id)

    return new_alerts


def list_firing_alerts() -> List[Alert]:
    """Return all currently firing alerts."""
    with _lock:
        return list(_firing_alerts.values())


def get_rule(rule_id: str) -> Optional[AlertRule]:
    with _lock:
        return _active_rules.get(rule_id)


def update_rule_state(rule_id: str, new_state: AlertState) -> AlertRule:
    with _lock:
        rule = _active_rules[rule_id]
        rule.state = new_state
        if new_state == AlertState.MUTED and rule_id in _firing_alerts:
            # Mute the firing alert too
            _firing_alerts.pop(rule_id, None)
    log.info("alert.rule.state_changed", rule_id=rule_id, state=new_state.value)
    return rule


def _auto_seed() -> None:
    """Register built-in alert rules."""
    for rule in _BUILTIN_RULES:
        register_rule(rule)
