"""ConnectorHub registry unit tests."""
from __future__ import annotations

import pytest

from apps.connector_hub.connectors.cli import CliConnector
from apps.connector_hub.models import Capability, ConnectorType
from apps.connector_hub.registry import (
    _auto_register,
    get,
    is_registered,
    list_all,
    list_ids,
    register,
)


class DummyConnector(CliConnector):
    """Test-only connector that doesn't require external deps."""

    def __init__(self, cid: str = "dummy"):
        super().__init__(connector_id=cid, name=f"Dummy {cid}")


def _reset_registry():
    """Clear the global registry between tests."""
    import apps.connector_hub.registry as reg

    reg._registry.clear()


class TestRegistry:
    """Registry tests."""

    def test_register_and_get(self):
        _reset_registry()
        c = DummyConnector("test-1")
        register(c)
        assert get("test-1").id == "test-1"

    def test_register_duplicate_warns(self):
        _reset_registry()
        c = DummyConnector("dup")
        register(c)
        # Second registration logs warning but doesn't raise
        register(c)
        assert list_ids() == ["dup"]

    def test_list_all(self):
        _reset_registry()
        register(DummyConnector("a"))
        register(DummyConnector("b"))
        ids = list_ids()
        assert set(ids) == {"a", "b"}

    def test_is_registered(self):
        _reset_registry()
        assert not is_registered("ghost")
        register(DummyConnector("ghost"))
        assert is_registered("ghost")

    def test_get_unknown_raises_KeyError(self):
        _reset_registry()
        with pytest.raises(KeyError):
            get("nonexistent")

    def test_auto_register_adds_piagent_cli(self):
        _reset_registry()
        _auto_register()
        assert "piagent-cli" in list_ids()
