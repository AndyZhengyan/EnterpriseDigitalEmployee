"""ConnectorHub FastAPI service — port 8003."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from apps.connector_hub import __version__
from apps.connector_hub.config import ConnectorHubSettings
from apps.connector_hub.errors import ConnectorHubError
from apps.connector_hub.models import (
    ConnectorListResponse,
    HubHealthResponse,
    InvokeRequest,
    InvokeResponse,
)
from apps.connector_hub.registry import _auto_register, get, list_all, list_ids
from common.tracing import get_logger

log = get_logger("connector_hub")

settings = ConnectorHubSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _auto_register()
    log.info(
        "connector_hub.started",
        port=settings.port,
        connectors=list_ids(),
    )
    yield
    log.info("connector_hub.stopped")


app = FastAPI(title="ConnectorHub", version=__version__, lifespan=lifespan)


@app.get("/connector-hub/health", response_model=HubHealthResponse)
async def hub_health() -> HubHealthResponse:
    """Overall health of ConnectorHub and its connectors."""
    from apps.connector_hub.registry import get_info_map

    info_map = get_info_map()
    all_healthy = all(info_map.values()) if info_map else True
    return HubHealthResponse(
        status="healthy" if all_healthy else "degraded",
        version=__version__,
        timestamp=datetime.now(timezone.utc),
        connectors=info_map,
    )


@app.get("/connectors", response_model=ConnectorListResponse)
async def list_connectors() -> ConnectorListResponse:
    """Return all registered connectors with their capabilities."""
    connectors = list_all()
    return ConnectorListResponse(
        connectors=[c.to_info() for c in connectors],
        total=len(connectors),
    )


@app.post("/connectors/{connector_id}/invoke", response_model=InvokeResponse)
async def invoke_connector(
    connector_id: str,
    req: InvokeRequest,
) -> InvokeResponse:
    """Invoke a capability on a registered connector."""
    start = time.monotonic()

    try:
        connector = get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    timeout = req.timeout_seconds or settings.default_timeout_seconds

    try:
        result = await connector.invoke(
            capability=req.capability,
            parameters=req.parameters,
            timeout_seconds=timeout,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return InvokeResponse(
            connector_id=connector_id,
            capability=req.capability,
            result=result,
            duration_ms=duration_ms,
        )

    except ConnectorHubError as e:
        log.warning(
            "connector.invoke.failed",
            connector_id=connector_id,
            capability=req.capability,
            code=e.code,
            error=e.message,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        return InvokeResponse(
            connector_id=connector_id,
            capability=req.capability,
            duration_ms=duration_ms,
            error=e.message,
        )


@app.get("/connectors/{connector_id}/health")
async def connector_health(connector_id: str) -> dict:
    """Check health of a specific connector."""
    try:
        connector = get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    start = time.monotonic()
    try:
        healthy = await connector.health_check()
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "connector_id": connector_id,
            "healthy": False,
            "latency_ms": duration_ms,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    duration_ms = int((time.monotonic() - start) * 1000)
    return {
        "connector_id": connector_id,
        "healthy": healthy,
        "latency_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
