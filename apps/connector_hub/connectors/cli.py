"""CLI connector — wraps PiAgentClient from apps.runtime.piagent_client."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from apps.connector_hub.connectors.base import Connector
from apps.connector_hub.errors import (
    ConnectorCapabilityNotFoundError,
    ConnectorExecutionFailedError,
    ConnectorTimeoutError,
)
from apps.connector_hub.models import Capability, ConnectorType
from common.tracing import get_logger

log = get_logger("connector_hub.cli")

CLI_CAPABILITIES = [
    Capability(
        name="agent_invoke",
        description="Send a message to the PiAgent and get a response",
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to send to the agent"},
                "session_id": {"type": "string", "description": "Optional session ID"},
            },
            "required": ["message"],
        },
        output_schema={"type": "object"},
        idempotent=True,
        risk_level="medium",
    ),
]


class CliConnector(Connector):
    """Connector that wraps PiAgentClient subprocess/CLI calls.

    This is the primary connector for pi-agent invocation, reusing the
    existing PiAgentClient from apps.runtime.
    """

    def __init__(
        self,
        connector_id: str = "piagent-cli",
        name: str = "PiAgent CLI",
        description: str = "PiAgent via subprocess CLI — wraps OpenClaw agent invocation",
        default_agent: str = "chat",
        default_timeout_seconds: int = 120,
    ) -> None:
        self._id = connector_id
        self._name = name
        self._description = description
        self._default_agent = default_agent
        self._default_timeout = default_timeout_seconds

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def type(self) -> ConnectorType:
        return ConnectorType.CLI

    def list_capabilities(self) -> list[Capability]:
        return CLI_CAPABILITIES

    async def invoke(
        self,
        capability: str,
        parameters: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> Any:
        if capability != "agent_invoke":
            raise ConnectorCapabilityNotFoundError(self.id, capability)

        message = parameters.get("message")
        if not message:
            raise ConnectorExecutionFailedError(self.id, reason="Missing required parameter: message")

        session_id = parameters.get("session_id")

        # Import lazily to avoid circular import at module level
        from apps.runtime.piagent_client import PiAgentClient

        client = PiAgentClient(
            agent_id=self._default_agent,
            timeout_seconds=timeout_seconds,
        )

        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                client.invoke_async(message, session_id=session_id),
                timeout=timeout_seconds,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            return {
                "run_id": result.run_id,
                "status": result.status,
                "summary": result.summary,
                "text": result.text,
                "duration_ms": duration_ms,
            }
        except asyncio.TimeoutError:
            raise ConnectorTimeoutError(self.id, timeout_seconds) from None

    async def health_check(self) -> bool:
        try:
            from apps.runtime.piagent_client import PiAgentClient

            client = PiAgentClient(agent_id=self._default_agent, timeout_seconds=5)
            # Lightweight smoke test: just try to invoke with a ping
            result = await asyncio.wait_for(
                client.invoke_async("ping", session_id=None),
                timeout=5,
            )
            return result.status == "ok"
        except Exception as e:
            log.warning("cli_connector.health_check.failed", error=str(e))
            return False
