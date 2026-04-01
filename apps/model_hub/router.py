"""ModelHub routing engine — selects model by task_type with fallback."""

from __future__ import annotations

import logging
from typing import Optional

from apps.model_hub.models import TaskType

log = logging.getLogger("model_hub.router")

# (provider_name, model_id)
ProviderModel = tuple[str, str]

# Fallback chain: first tries primary, then fallbacks in order
ROUTING_TABLE: dict[TaskType, list[ProviderModel]] = {
    TaskType.PLANNING: [
        ("minimax-cn", "MiniMax-M2.7"),
        ("anthropic", "claude-opus-4-5-5"),
    ],
    TaskType.FAST: [
        ("minimax-cn", "MiniMax-M2.7"),
    ],
    TaskType.CODE: [
        ("minimax-cn", "MiniMax-M2.7"),
        ("anthropic", "claude-sonnet-4-5"),
    ],
}


class ModelRouter:
    """Routes requests to appropriate model providers with fallback."""

    def __init__(self, available_providers: dict[str, list[str]] | None = None):
        """
        available_providers: {provider_name: [model_ids]} — filters routing table
        If None, all models in ROUTING_TABLE are considered available.
        """
        self._available = available_providers or {}

    def route(
        self,
        task_type: TaskType,
        preferred: Optional[ProviderModel] = None,
    ) -> list[ProviderModel]:
        """
        Returns an ordered list of (provider, model) to try.

        - preferred: if provided, prepends to the chain (user override)
        - task_type: selects the base chain from ROUTING_TABLE
        - Returns only providers that are "available" (in self._available)
        """
        chain: list[ProviderModel] = []

        if preferred:
            if self._is_available(preferred):
                chain.append(preferred)

        for candidate in ROUTING_TABLE.get(task_type, []):
            if candidate not in chain and self._is_available(candidate):
                chain.append(candidate)

        return chain

    def _is_available(self, pm: ProviderModel) -> bool:
        provider, model = pm
        if not self._available:
            return True  # Everything available if no filter set
        return provider in self._available and model in self._available[provider]

    def register_provider(self, provider: str, models: list[str]) -> None:
        """Register a provider that has become available."""
        self._available[provider] = models
        log.info("provider_registered", provider=provider, models=models)
