"""ConnectorHub request/response models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConnectorType(str, Enum):
    """Connector type (priority order)."""

    CLI = "cli"
    MCP = "mcp"
    API = "api"
    CU = "cu"  # Custom


class Capability(BaseModel):
    """Single capability of a connector."""

    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    idempotent: bool = True
    risk_level: str = "low"  # low / medium / high
    requires_approval: bool = False

    model_config = {"extra": "ignore"}


class ConnectorInfo(BaseModel):
    """Registered connector descriptor."""

    id: str
    name: str
    description: str = ""
    type: ConnectorType
    capabilities: List[Capability] = Field(default_factory=list)
    healthy: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


class ConnectorListResponse(BaseModel):
    """Response for GET /connectors."""

    connectors: List[ConnectorInfo]
    total: int


class InvokeRequest(BaseModel):
    """Request for POST /connectors/{id}/invoke."""

    capability: str = Field(..., description="Capability name to invoke")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=600)
    employee_id: Optional[str] = None

    model_config = {"extra": "ignore"}


class InvokeResponse(BaseModel):
    """Response for POST /connectors/{id}/invoke."""

    connector_id: str
    capability: str
    result: Any = None
    duration_ms: int = 0
    error: Optional[str] = None

    model_config = {"extra": "ignore"}


class HealthResponse(BaseModel):
    """Response for GET /connectors/{id}/health."""

    connector_id: str
    healthy: bool
    latency_ms: int = 0
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


class HubHealthResponse(BaseModel):
    """Response for GET /connector-hub/health."""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    connectors: Dict[str, bool] = Field(default_factory=dict)

    model_config = {"extra": "ignore"}
