"""ConnectorHub configuration."""

from __future__ import annotations

from common.config import BaseSettings


class ConnectorHubSettings(BaseSettings):
    """ConnectorHub settings."""

    model_config = {"env_prefix": "CONNECTORHUB_", "extra": "ignore"}

    host: str = "127.0.0.1"
    port: int = 8003
    default_timeout_seconds: int = 120
    max_concurrent_invocations: int = 50
    health_check_interval_seconds: int = 60
