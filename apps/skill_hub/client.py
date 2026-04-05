"""SkillHub client — singleton used by RuntimeExecutor."""

from __future__ import annotations

from typing import Any

import httpx

from apps.skill_hub.models import InvokeRequest, InvokeResponse, Skill, SkillListResponse

__version__ = "0.1.0"


class SkillHubClient:
    """Singleton HTTP client for SkillHub.

    Usage::

        client = SkillHubClient()
        skills = await client.list_skills()
        resp = await client.invoke_skill("approval", {"employee_id": "e-001"})
    """

    _instance: SkillHubClient | None = None

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8004",
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @classmethod
    def get_instance(cls, **kwargs: Any) -> SkillHubClient:
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    async def list_skills(
        self,
        status: str | None = None,
        level: str | None = None,
    ) -> SkillListResponse:
        """List all registered skills."""
        params = {}
        if status:
            params["status"] = status
        if level:
            params["level"] = level
        resp = await self._client.get(f"{self._base_url}/skills", params=params)
        resp.raise_for_status()
        return SkillListResponse(**resp.json())

    async def get_skill(self, skill_id: str) -> Skill:
        """Get a skill by ID."""
        resp = await self._client.get(f"{self._base_url}/skills/{skill_id}")
        resp.raise_for_status()
        return Skill(**resp.json())

    async def invoke_skill(
        self,
        skill_id: str,
        parameters: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
        employee_id: str | None = None,
    ) -> InvokeResponse:
        """Invoke a skill by ID."""
        req = InvokeRequest(
            parameters=parameters or {},
            timeout_seconds=timeout_seconds,
            employee_id=employee_id,
        )
        resp = await self._client.post(
            f"{self._base_url}/skills/{skill_id}/invoke",
            json=req.model_dump(mode="json"),
            timeout=timeout_seconds or self._timeout,
        )
        resp.raise_for_status()
        return InvokeResponse(**resp.json())

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/skill-hub/health")
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
        SkillHubClient._instance = None
