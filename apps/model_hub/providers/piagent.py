"""PiAgent provider — calls the sidecar HTTP server."""

from __future__ import annotations

from typing import Any

import httpx

from apps.model_hub.errors import ModelProviderError, ModelTimeoutError
from apps.model_hub.models import ChatResponse, ModelInfo
from apps.model_hub.providers.base import ModelProvider
from common.tracing import get_logger

log = get_logger("model_hub.provider.piagent")

# Models this provider exposes (pi-mono supports multiple providers via env keys)
PIAGENT_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="minimax-cn/MiniMax-M2.7",
        name="MiniMax-M2.7",
        provider="minimax-cn",
        supports=["text"],
    ),
    ModelInfo(
        id="anthropic/claude-opus-4-5-5",
        name="Claude Opus 4.5",
        provider="anthropic",
        supports=["text"],
    ),
    ModelInfo(
        id="anthropic/claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        supports=["text"],
    ),
]


class PiAgentProvider(ModelProvider):
    """Calls the pi-mono sidecar HTTP server.

    The sidecar handles provider/auth selection internally based on
    the provider field in each request.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8090", timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "piagent"

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_key_env(self) -> str:
        return ""  # Not applicable — sidecar handles auth

    def list_models(self) -> list[ModelInfo]:
        return PIAGENT_MODELS

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        session_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        thinking_level: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        timeout_seconds: int = 120,
    ) -> ChatResponse:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))

        # Split provider/model from model string if needed
        if "/" in model:
            provider, model_id = model.split("/", 1)
        else:
            provider = "minimax-cn"
            model_id = model

        payload: dict[str, Any] = {
            "provider": provider,
            "model": model_id,
            "messages": messages,
        }
        if session_id:
            payload["session_id"] = session_id

        try:
            response = await self._client.post(
                f"{self._base_url}/chat",
                json=payload,
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as e:
            raise ModelTimeoutError(
                f"PiAgent sidecar timed out after {timeout_seconds}s",
                provider=self.name,
                model=model,
            ) from e
        except httpx.RequestError as e:
            raise ModelProviderError(
                f"PiAgent sidecar unreachable: {e}",
                provider=self.name,
                model=model,
            ) from e

        if response.status_code != 200:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            detail = body.get("error", response.text)
            raise ModelProviderError(
                f"PiAgent returned {response.status_code}: {detail}",
                provider=self.name,
                model=model,
            )

        data = response.json()
        return ChatResponse(
            content=data.get("content", ""),
            model=data.get("model", model),
            provider=data.get("provider", self.name),
            latency_ms=data.get("latency_ms", 0),
            finish_reason=data.get("finish_reason"),
            tool_calls=data.get("tool_calls", []),
            raw=data,
        )

    async def health_check(self) -> bool:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
        try:
            response = await self._client.get(f"{self._base_url}/health")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
