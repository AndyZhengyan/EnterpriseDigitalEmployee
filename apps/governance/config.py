"""Governance service configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GovernanceSettings(BaseModel):
    """Settings for the Governance service."""

    port: int = Field(default=8007, description="Governance service HTTP port")
    jwt_secret: str = Field(default="dev-secret-change-in-production", description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiry_seconds: int = Field(default=3600, ge=60, description="JWT token expiry")

    # RBAC defaults
    default_role: str = Field(default="employee_user", description="Default role for new users")

    model_config = {"extra": "ignore"}
