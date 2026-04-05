"""ModelHub usage tracker tests."""

from __future__ import annotations

import threading
import time

import pytest

from apps.model_hub.models import UsageRecord
from apps.model_hub.usage import UsageTracker


class TestUsageTracker:
    """UsageTracker tests."""

    def test_record_accumulates_tokens(self):
        """record() accumulates tokens and cost for the same (employee, date) key."""
        tracker = UsageTracker()
        tracker.record(
            "emp-1", prompt_tokens=100, completion_tokens=50, cost_usd=0.01, provider="minimax-cn", model="MiniMax-M2.7"
        )
        tracker.record(
            "emp-1",
            prompt_tokens=200,
            completion_tokens=100,
            cost_usd=0.02,
            provider="minimax-cn",
            model="MiniMax-M2.7",
        )

        results = tracker.get_usage("emp-1", days=1)
        assert len(results) == 1
        rec = results[0]
        assert rec.employee_id == "emp-1"
        assert rec.prompt_tokens == 300
        assert rec.completion_tokens == 150
        assert rec.total_tokens == 450
        assert rec.cost_usd == 0.03
        assert rec.request_count == 2

    def test_get_usage_different_employees(self):
        """Different employees have separate usage records."""
        tracker = UsageTracker()
        tracker.record("emp-1", 10, 5, 0.001, "minimax-cn", "MiniMax-M2.7")
        tracker.record("emp-2", 20, 10, 0.002, "minimax-cn", "MiniMax-M2.7")

        emp1 = tracker.get_usage("emp-1", days=1)
        emp2 = tracker.get_usage("emp-2", days=1)
        assert emp1[0].prompt_tokens == 10
        assert emp2[0].prompt_tokens == 20

    def test_get_total_sums_all_days(self):
        """get_total() sums across all days."""
        tracker = UsageTracker()
        # Records on same day (today) — get_total should sum them
        tracker.record("emp-1", 100, 50, 0.01, "minimax-cn", "MiniMax-M2.7")
        tracker.record("emp-1", 200, 100, 0.02, "anthropic", "claude-opus-4-5-5")

        total = tracker.get_total("emp-1")
        assert total.prompt_tokens == 300
        assert total.completion_tokens == 150
        assert total.total_tokens == 450
        assert total.cost_usd == 0.03
        assert total.request_count == 2

    def test_thread_safety(self):
        """record() is safe to call concurrently from multiple threads."""
        tracker = UsageTracker()
        errors: list[Exception] = []

        def record_batch(employee_id: str) -> None:
            try:
                for _ in range(100):
                    tracker.record(employee_id, 1, 1, 0.0001, "minimax-cn", "MiniMax-M2.7")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=record_batch, args=("emp-A",))
        t2 = threading.Thread(target=record_batch, args=("emp-B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        total_a = tracker.get_total("emp-A")
        total_b = tracker.get_total("emp-B")
        assert total_a.request_count == 100
        assert total_b.request_count == 100
