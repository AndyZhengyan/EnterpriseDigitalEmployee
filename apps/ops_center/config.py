"""OpsCenter configuration."""

from __future__ import annotations

from common.config import BaseSettings


class OpsCenterSettings(BaseSettings):
    """OpsCenter settings."""

    model_config = {"env_prefix": "OPSCENTER_", "extra": "ignore"}

    host: str = "127.0.0.1"
    port: int = 8006
