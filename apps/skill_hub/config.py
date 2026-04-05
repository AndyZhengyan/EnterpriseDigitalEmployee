"""SkillHub configuration."""

from __future__ import annotations

from common.config import BaseSettings


class SkillHubSettings(BaseSettings):
    """SkillHub settings."""

    model_config = {"env_prefix": "SKILLHUB_", "extra": "ignore"}

    host: str = "127.0.0.1"
    port: int = 8004
    default_timeout_seconds: int = 120
