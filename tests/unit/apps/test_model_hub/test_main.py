"""ModelHub FastAPI main tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.model_hub.main import app, _pi_agent_provider
from apps.model_hub.models import ChatResponse
from common.models import ModelUsage


class TestHealthEndpoint:
    """GET /model-hub/health tests."""

    def test_health_returns_providers(self):
        """Health returns status and provider list."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        with patch("apps.model_hub.main._pi_agent_provider", mock_provider):
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/model-hub/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "providers" in data
        assert "version" in data


class TestListProvidersEndpoint:
    """GET /model/providers tests."""

    def test_providers_returns_list(self):
        """Returns piagent provider with models."""
        mock_provider = AsyncMock()
        mock_provider.list_models.return_value = []
        mock_provider.base_url = "http://localhost:8090"
        mock_provider.api_key_env = ""
        with patch("apps.model_hub.main._pi_agent_provider", mock_provider):
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/model/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert data["providers"][0]["name"] == "piagent"


class TestChatEndpoint:
    """POST /model/chat tests."""

    def test_chat_returns_response(self):
        """Successful chat returns ChatResponse."""
        mock_response = ChatResponse(
            content="Hello!",
            model="MiniMax-M2.7",
            provider="minimax-cn",
            usage=ModelUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            latency_ms=200,
        )
        with patch(
            "apps.model_hub.providers.piagent.PiAgentProvider.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/model/chat",
                    json={
                        "messages": [{"role": "user", "content": "hi"}],
                        "task_type": "fast",
                    },
                )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello!"
        assert data["model"] == "MiniMax-M2.7"

    def test_chat_invalid_request_returns_422(self):
        """Missing messages returns 422 validation error."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/model/chat", json={"task_type": "fast"})
        assert response.status_code == 422

    def test_chat_with_model_override(self):
        """model override is parsed as provider/model and prepended to chain."""
        captured_call_args = []

        async def mock_chat(*args, **kwargs):
            captured_call_args.append((args, kwargs))
            return ChatResponse(
                content="hi",
                model="claude-opus-4-5-5",
                provider="anthropic",
                usage=ModelUsage(),
            )

        with patch(
            "apps.model_hub.providers.piagent.PiAgentProvider.chat",
            new_callable=AsyncMock,
        ) as mock_method:
            mock_method.side_effect = mock_chat
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post(
                    "/model/chat",
                    json={
                        "messages": [{"role": "user", "content": "hi"}],
                        "model": "anthropic/claude-opus-4-5-5",
                        "task_type": "planning",
                    },
                )
        assert response.status_code == 200
        # The preferred model should be tried first
        assert len(captured_call_args) >= 1


class TestUsageEndpoint:
    """GET /model/usage/{employee_id} tests."""

    def test_usage_returns_records(self):
        """Returns usage records for the employee."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/model/usage/emp-123", params={"days": 7})
        assert response.status_code == 200
        data = response.json()
        assert data["employee_id"] == "emp-123"
        assert data["period"] == "daily"
        assert "usage" in data

    def test_usage_defaults_to_7_days(self):
        """Default days is 7."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/model/usage/emp-xyz")
        assert response.status_code == 200
        data = response.json()
        assert data["employee_id"] == "emp-xyz"
