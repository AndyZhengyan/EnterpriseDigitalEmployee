"""ModelHub client — singleton used by RuntimeExecutor."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from apps.model_hub.models import ChatRequest, ChatResponse, TaskType

log = logging.getLogger("model_hub.client")

__version__ = "0.1.0"


class ModelHubClient:
    """Singleton HTTP client for ModelHub.

    Usage::

        client = ModelHubClient()
        resp = await client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            task_type="fast",
            session_id="sess-123",
        )
    """

    _instance: ModelHubClient | None = None

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8002",
        timeout: int = 120,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @classmethod
    def get_instance(cls, **kwargs: Any) -> ModelHubClient:
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    async def chat(
        self,
        messages: list[dict[str, Any]],
        task_type: str = "fast",
        model: str | None = None,
        session_id: str | None = None,
        employee_id: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        thinking_level: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        timeout_seconds: int = 120,
    ) -> ChatResponse:
        req = ChatRequest(
            messages=messages,
            model=model,
            task_type=TaskType(task_type),
            session_id=session_id,
            employee_id=employee_id,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_level=thinking_level,
            tools=tools,
            timeout_seconds=timeout_seconds,
        )
        response = await self._client.post(
            f"{self._base_url}/model/chat",
            json=req.model_dump(mode="json"),
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return ChatResponse(**response.json())

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/model-hub/health")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
        ModelHubClient._instance = None
