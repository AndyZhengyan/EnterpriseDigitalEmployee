"""ModelHub usage tracking — in-memory with daily aggregation."""

from __future__ import annotations

import threading
from collections import defaultdict
from datetime import date
from typing import Dict

from apps.model_hub.models import UsageRecord


class UsageTracker:
    """Thread-safe in-memory usage tracker, keyed by (employee_id, date_str)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # {(employee_id, date_str): UsageRecord}
        self._records: Dict[tuple[str, str], UsageRecord] = defaultdict(
            lambda: UsageRecord(employee_id="", date=str(date.today()))
        )

    def record(
        self,
        employee_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        provider: str,
        model: str,
    ) -> None:
        today = date.today().isoformat()
        key = (employee_id, today)
        with self._lock:
            rec = self._records[key]
            rec.employee_id = employee_id
            rec.date = today
            rec.prompt_tokens += prompt_tokens
            rec.completion_tokens += completion_tokens
            rec.total_tokens += prompt_tokens + completion_tokens
            rec.cost_usd += cost_usd
            rec.request_count += 1

    def get_usage(self, employee_id: str, days: int = 7) -> list[UsageRecord]:
        today = date.today()
        results: list[UsageRecord] = []
        with self._lock:
            for i in range(days):
                d = today.replace(day=max(1, today.day - i))
                key = (employee_id, d.isoformat())
                if key in self._records:
                    results.append(self._records[key])
        return results

    def get_total(self, employee_id: str) -> UsageRecord:
        today = date.today().isoformat()
        total = UsageRecord(employee_id=employee_id, date=today)
        with self._lock:
            for (eid, _), rec in self._records.items():
                if eid == employee_id:
                    total.prompt_tokens += rec.prompt_tokens
                    total.completion_tokens += rec.completion_tokens
                    total.total_tokens += rec.total_tokens
                    total.cost_usd += rec.cost_usd
                    total.request_count += rec.request_count
        return total
