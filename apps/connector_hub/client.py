"""ConnectorHub client — singleton used by RuntimeExecutor."""

from __future__ import annotations

from typing import Any

import httpx

from apps.connector_hub.models import (
    ConnectorInfo,
    ConnectorListResponse,
    InvokeRequest,
    InvokeResponse,
)

__version__ = "0.1.0"


class ConnectorHubClient:
    """Singleton HTTP client for ConnectorHub.

    Usage::

        client = ConnectorHubClient()
        connectors = await client.list_connectors()
        resp = await client.invoke("pi-agent", "agent_invoke", {"task": "..."})
    """

    _instance: ConnectorHubClient | None = None

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8003",
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @classmethod
    def get_instance(cls, **kwargs: Any) -> ConnectorHubClient:
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    async def list_connectors(self) -> ConnectorListResponse:
        """List all registered connectors."""
        resp = await self._client.get(f"{self._base_url}/connectors")
        resp.raise_for_status()
        return ConnectorListResponse(**resp.json())

    async def get_connector(self, connector_id: str) -> ConnectorInfo:
        """Get a connector by ID."""
        resp = await self._client.get(f"{self._base_url}/connectors/{connector_id}")
        resp.raise_for_status()
        return ConnectorInfo(**resp.json())

    async def invoke(
        self,
        connector_id: str,
        capability: str,
        parameters: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
        employee_id: str | None = None,
    ) -> InvokeResponse:
        """Invoke a capability on a registered connector."""
        req = InvokeRequest(
            capability=capability,
            parameters=parameters or {},
            timeout_seconds=timeout_seconds,
            employee_id=employee_id,
        )
        resp = await self._client.post(
            f"{self._base_url}/connectors/{connector_id}/invoke",
            json=req.model_dump(mode="json"),
            timeout=timeout_seconds or self._timeout,
        )
        resp.raise_for_status()
        return InvokeResponse(**resp.json())

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/connector-hub/health")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
        ConnectorHubClient._instance = None
