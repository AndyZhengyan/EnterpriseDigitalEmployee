"""PiAgentProvider unit tests (mocked httpx)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import httpx

from apps.model_hub.models import ChatResponse, ModelInfo
from apps.model_hub.providers.piagent import PiAgentProvider


class TestPiAgentProvider:
    """PiAgentProvider tests."""

    def test_list_models_returns_static_list(self):
        """list_models() returns the known model list."""
        provider = PiAgentProvider()
        models = provider.list_models()
        assert len(models) == 3
        ids = [m.id for m in models]
        assert "minimax-cn/MiniMax-M2.7" in ids
        assert "anthropic/claude-opus-4-5-5" in ids

    def test_properties(self):
        """name, base_url, api_key_env are exposed."""
        provider = PiAgentProvider(base_url="http://localhost:9999")
        assert provider.name == "piagent"
        assert provider.base_url == "http://localhost:9999"
        assert provider.api_key_env == ""

    @pytest.mark.asyncio
    async def test_chat_splits_provider_model(self):
        """When model contains '/', it is split into provider + model_id."""
        provider = PiAgentProvider(base_url="http://localhost:8090")
        mock_response = httpx.Response(
            200,
            json={"content": "hello", "model": "MiniMax-M2.7", "provider": "minimax-cn", "latency_ms": 100},
        )
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.post.return_value = mock_response
            resp = await provider.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="minimax-cn/MiniMax-M2.7",
            )
            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs["json"]
            assert payload["provider"] == "minimax-cn"
            assert payload["model"] == "MiniMax-M2.7"
            assert resp.content == "hello"

    @pytest.mark.asyncio
    async def test_chat_no_slash_defaults_to_minimax(self):
        """model without '/' defaults provider to minimax-cn."""
        provider = PiAgentProvider()
        mock_response = httpx.Response(
            200,
            json={"content": "hi", "model": "MiniMax-M2.7", "provider": "minimax-cn", "latency_ms": 50},
        )
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.post.return_value = mock_response
            await provider.chat(messages=[], model="MiniMax-M2.7")
            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["provider"] == "minimax-cn"
            assert payload["model"] == "MiniMax-M2.7"

    @pytest.mark.asyncio
    async def test_chat_passes_session_id(self):
        """session_id is forwarded in the payload."""
        provider = PiAgentProvider()
        mock_response = httpx.Response(
            200,
            json={"content": "", "model": "MiniMax-M2.7", "provider": "minimax-cn", "latency_ms": 10},
        )
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.post.return_value = mock_response
            await provider.chat(messages=[], model="MiniMax-M2.7", session_id="sess-abc")
            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["session_id"] == "sess-abc"

    @pytest.mark.asyncio
    async def test_chat_timeout_raises_ModelTimeoutError(self):
        """httpx.TimeoutException raises ModelTimeoutError."""
        provider = PiAgentProvider()
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            from apps.model_hub.errors import ModelTimeoutError
            with pytest.raises(ModelTimeoutError):
                await provider.chat(messages=[], model="MiniMax-M2.7", timeout_seconds=5)

    @pytest.mark.asyncio
    async def test_chat_non_200_raises_ModelProviderError(self):
        """Non-200 response raises ModelProviderError."""
        provider = PiAgentProvider()
        mock_response = httpx.Response(500, json={"error": "模型服务异常", "code": "PROVIDER_ERROR"})
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.post.return_value = mock_response
            from apps.model_hub.errors import ModelProviderError
            with pytest.raises(ModelProviderError):
                await provider.chat(messages=[], model="MiniMax-M2.7")

    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self):
        """health_check returns True when /health returns 200."""
        provider = PiAgentProvider()
        mock_response = httpx.Response(200, json={"status": "ok"})
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.get.return_value = mock_response
            result = await provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self):
        """health_check returns False when request fails."""
        provider = PiAgentProvider()
        with patch.object(provider, "_client", AsyncMock()) as mock_client:
            mock_client.get.side_effect = httpx.RequestError("connection refused")
            result = await provider.health_check()
            assert result is False
