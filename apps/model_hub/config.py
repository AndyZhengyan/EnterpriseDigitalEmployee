"""ModelHub configuration."""

from __future__ import annotations

from common.config import BaseSettings


class ModelHubSettings(BaseSettings):
    """ModelHub service configuration."""

    model_config = {"env_prefix": "MODELHUB_", "extra": "ignore"}

    # Service binding
    host: str = "127.0.0.1"
    port: int = 8002

    # Sidecar HTTP server port (spawned by piagent.py provider)
    sidecar_http_port: int = 8090

    # Routing
    default_task_type: str = "fast"  # fast | planning | code

    # Quotas (per employee per day, 0 = unlimited)
    daily_token_limit: int = 0

    # Health check timeout for providers (seconds)
    provider_timeout_seconds: int = 120
