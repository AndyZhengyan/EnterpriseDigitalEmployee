"""Abstract base class for ModelHub providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from apps.model_hub.models import ChatResponse, ModelInfo


class ModelProvider(ABC):
    """Abstract model provider interface.

    Each provider wraps a specific LLM backend (pi-mono sidecar, OpenAI, Anthropic, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name, e.g. 'minimax-cn', 'anthropic'."""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL of the provider's HTTP endpoint."""

    @property
    @abstractmethod
    def api_key_env(self) -> str:
        """Environment variable name that holds the API key."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        session_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        thinking_level: str | None = None,
        tools: List[Dict[str, Any]] | None = None,
        timeout_seconds: int = 120,
    ) -> ChatResponse:
        """Send a chat request and return the response."""

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """Return all models this provider supports."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and responding."""
