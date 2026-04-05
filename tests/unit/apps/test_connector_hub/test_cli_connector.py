"""ConnectorHub CLI connector unit tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from apps.connector_hub.connectors.cli import CliConnector
from apps.connector_hub.errors import ConnectorCapabilityNotFoundError, ConnectorTimeoutError
from apps.connector_hub.models import ConnectorType


class TestCliConnector:
    """CliConnector tests."""

    def test_properties(self):
        """Connector exposes correct id, name, type."""
        c = CliConnector()
        assert c.id == "piagent-cli"
        assert c.name == "PiAgent CLI"
        assert c.type == ConnectorType.CLI
        assert "agent_invoke" in [cap.name for cap in c.list_capabilities()]

    def test_custom_id_and_name(self):
        """Custom connector_id and name are respected."""
        c = CliConnector(
            connector_id="my-agent",
            name="My Custom Agent",
        )
        assert c.id == "my-agent"
        assert c.name == "My Custom Agent"

    def test_to_info(self):
        """to_info returns ConnectorInfo with correct fields."""
        c = CliConnector()
        info = c.to_info()
        assert info.id == "piagent-cli"
        assert info.type == ConnectorType.CLI
        assert len(info.capabilities) == 1
        assert info.capabilities[0].name == "agent_invoke"

    @pytest.mark.asyncio
    async def test_invoke_unknown_capability_raises(self):
        """Unknown capability raises ConnectorCapabilityNotFoundError."""
        c = CliConnector()
        with pytest.raises(ConnectorCapabilityNotFoundError):
            await c.invoke("unknown_cap", {})

    @pytest.mark.asyncio
    async def test_invoke_missing_message_raises(self):
        """agent_invoke without message raises."""
        c = CliConnector()
        with pytest.raises(Exception):  # ExecutionFailed
            await c.invoke("agent_invoke", parameters={})

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """Successful invocation returns result dict."""
        c = CliConnector()

        mock_result = AsyncMock()
        mock_result.run_id = "run-123"
        mock_result.status = "ok"
        mock_result.summary = "Done"
        mock_result.text = "Hello!"

        with patch(
            "apps.runtime.piagent_client.PiAgentClient"
        ) as MockClient:
            mock_instance = AsyncMock()
            mock_instance.invoke_async.return_value = mock_result
            MockClient.return_value = mock_instance

            result = await c.invoke(
                "agent_invoke",
                parameters={"message": "hello"},
                timeout_seconds=30,
            )

        assert result["run_id"] == "run-123"
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_invoke_timeout_raises_ConnectorTimeoutError(self):
        """Timeout raises ConnectorTimeoutError."""
        c = CliConnector()

        import asyncio

        with patch(
            "apps.runtime.piagent_client.PiAgentClient"
        ) as MockClient:
            mock_instance = AsyncMock()
            mock_instance.invoke_async.side_effect = asyncio.TimeoutError()
            MockClient.return_value = mock_instance

            with pytest.raises(ConnectorTimeoutError):
                await c.invoke("agent_invoke", parameters={"message": "hi"})
