"""Abstract base class for connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from apps.connector_hub.models import Capability, ConnectorInfo, ConnectorType


class Connector(ABC):
    """Abstract connector interface.

    Each connector wraps a specific integration mechanism:
    CLI (PiAgentClient), MCP, API, or custom.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique connector ID."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable connector name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this connector does."""

    @property
    @abstractmethod
    def type(self) -> ConnectorType:
        """Connector type (cli, mcp, api, cu)."""

    @abstractmethod
    def list_capabilities(self) -> List[Capability]:
        """Return all capabilities this connector supports."""

    @abstractmethod
    async def invoke(
        self,
        capability: str,
        parameters: Dict[str, Any],
        timeout_seconds: int = 120,
    ) -> Any:
        """Invoke a capability with given parameters."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the connector is reachable and healthy."""

    def to_info(self) -> ConnectorInfo:
        """Return a ConnectorInfo descriptor for this connector."""
        return ConnectorInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            type=self.type,
            capabilities=self.list_capabilities(),
            healthy=True,
            config={},
        )
