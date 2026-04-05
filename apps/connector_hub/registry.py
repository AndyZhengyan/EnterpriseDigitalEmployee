"""ConnectorHub registry — manages connector lifecycle and discovery."""

from __future__ import annotations

from typing import Dict, List

from apps.connector_hub.connectors.base import Connector
from apps.connector_hub.connectors.cli import CliConnector
from common.tracing import get_logger

log = get_logger("connector_hub.registry")

# Global registry: connector_id -> Connector instance
_registry: Dict[str, Connector] = {}


def register(connector: Connector) -> None:
    """Register a connector in the global registry."""
    if connector.id in _registry:
        log.warning("connector.already_registered", connector_id=connector.id)
    _registry[connector.id] = connector
    log.info("connector.registered", connector_id=connector.id, type=connector.type.value)


def get(connector_id: str) -> Connector:
    """Get a connector by ID. Raises KeyError if not found."""
    return _registry[connector_id]


def list_all() -> List[Connector]:
    """Return all registered connectors."""
    return list(_registry.values())


def list_ids() -> List[str]:
    """Return IDs of all registered connectors."""
    return list(_registry.keys())


def get_info_map() -> Dict[str, bool]:
    """Return {connector_id: healthy} for all connectors."""
    return {cid: c.to_info().healthy for cid, c in _registry.items()}


def is_registered(connector_id: str) -> bool:
    """Return True if connector is registered."""
    return connector_id in _registry


def _auto_register() -> None:
    """Auto-register built-in connectors."""
    register(CliConnector())
    log.info("connector_hub.auto_registered", count=len(_registry))
