"""OpsCenter alert engine tests."""

from __future__ import annotations

import pytest

from apps.ops_center.engine import (
    _eval_condition,
    _firing_alerts,
    _active_rules,
    evaluate_rules,
    get_rule,
    list_firing_alerts,
    list_rules,
    register_rule,
    update_rule_state,
)
from apps.ops_center.models import AlertRule, AlertSeverity, AlertState


def _reset():
    _active_rules.clear()
    _firing_alerts.clear()


class TestAlertEngine:
    """Alert engine tests."""

    def test_register_rule(self):
        _reset()
        rule = AlertRule(
            id="test-rule",
            name="Test Alert",
            metric="task_failure_rate",
            condition=">=",
            threshold=0.1,
        )
        register_rule(rule)
        assert get_rule("test-rule") is not None
        assert len(list_rules()) == 1

    def test_evaluate_fires_when_condition_met(self):
        _reset()
        rule = AlertRule(
            id="high-rate",
            name="High Rate",
            metric="task_failure_rate",
            condition="<=",
            threshold=0.1,  # stub _ops() returns 0.05, so 0.05 <= 0.1 → fires
            severity=AlertSeverity.ERROR,
        )
        register_rule(rule)
        alerts = evaluate_rules()
        assert len(alerts) == 1
        assert alerts[0].rule_id == "high-rate"

    def test_evaluate_resolves_when_condition_clears(self):
        _reset()
        rule = AlertRule(
            id="high-rate-2",
            name="High Rate 2",
            metric="task_failure_rate",
            condition=">=",
            threshold=1.0,  # Will not fire (0.05 < 1.0)
            severity=AlertSeverity.ERROR,
        )
        register_rule(rule)

        # First evaluation: doesn't fire
        alerts = evaluate_rules()
        assert len(alerts) == 0
        assert len(list_firing_alerts()) == 0

    def test_muted_rule_does_not_fire(self):
        _reset()
        rule = AlertRule(
            id="muted-test",
            name="Muted Test",
            metric="task_failure_rate",
            condition=">=",
            threshold=0.0,
            severity=AlertSeverity.INFO,
            state=AlertState.MUTED,
        )
        register_rule(rule)
        alerts = evaluate_rules()
        assert len(alerts) == 0

    def test_mute_resolves_firing_alert(self):
        _reset()
        rule = AlertRule(
            id="mute-fire",
            name="Mute Fire",
            metric="task_failure_rate",
            condition=">=",
            threshold=0.0,  # Always fires
            severity=AlertSeverity.WARNING,
        )
        register_rule(rule)
        evaluate_rules()
        assert len(list_firing_alerts()) == 1

        # Mute the rule
        update_rule_state("mute-fire", AlertState.MUTED)
        assert len(list_firing_alerts()) == 0

    def test_builtin_rules_registered(self):
        _reset()
        from apps.ops_center.engine import _auto_seed

        _auto_seed()
        assert len(list_rules()) >= 3  # At least 3 built-in rules


class TestEvalCondition:
    """Condition evaluation tests."""

    @pytest.mark.parametrize(
        "condition,threshold,value,expected",
        [
            (">", 0.5, 0.8, True),
            (">", 0.5, 0.3, False),
            (">=", 0.5, 0.5, True),
            ("<", 0.5, 0.3, True),
            ("<=", 0.5, 0.5, True),
            ("==", 0.5, 0.5, True),
            ("!=", 0.5, 0.3, True),
        ],
    )
    def test_eval_conditions(self, condition, threshold, value, expected):
        assert _eval_condition(value, condition, threshold) == expected
