"""KnowledgeHub client — singleton used by RuntimeExecutor for RAG context enrichment."""

from __future__ import annotations

from typing import Any

import httpx

from apps.knowledge_hub.models import (
    RetrievalStrategy,
    SearchRequest,
    SearchResponse,
)

__version__ = "0.1.0"


class KnowledgeHubClient:
    """Singleton HTTP client for KnowledgeHub.

    Usage::

        client = KnowledgeHubClient()
        results = await client.search("vacation policy", top_k=5)
    """

    _instance: KnowledgeHubClient | None = None

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8005",
        timeout: int = 30,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @classmethod
    def get_instance(cls, **kwargs: Any) -> KnowledgeHubClient:
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    async def search(
        self,
        query: str,
        top_k: int = 5,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        similarity_threshold: float | None = None,
        employee_id: str | None = None,
    ) -> SearchResponse:
        """Search knowledge base and return relevant documents."""
        req = SearchRequest(
            query=query,
            top_k=top_k,
            strategy=strategy,
            similarity_threshold=similarity_threshold,
            employee_id=employee_id,
        )
        resp = await self._client.post(
            f"{self._base_url}/knowledge/search",
            json=req.model_dump(mode="json"),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return SearchResponse(**resp.json())

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/knowledge-hub/health")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
        KnowledgeHubClient._instance = None
