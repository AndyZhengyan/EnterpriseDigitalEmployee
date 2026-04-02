"""Config Center FastAPI service — port 8008."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException

from apps.config_center import __version__
from apps.config_center.models import (
    ConfigChangeType,
    ConfigItem,
    ConfigListResponse,
    ConfigNamespace,
    ConfigStatus,
    ConfigVersionListResponse,
    Subscriber,
    SubscriberRegisterRequest,
)
from apps.config_center.push import push_sync
from apps.config_center.store import (
    deprecate_item,
    get_item,
    get_or_create_namespace,
    get_versions,
    list_changes,
    list_items,
    list_namespaces,
    list_subscribers,
    publish_item,
    register_subscriber,
    rollback_to_version,
    seed_defaults,
    set_item,
    unregister_subscriber,
)
from common.tracing import get_logger

log = get_logger("config_center")


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_defaults()
    log.info("config_center.started", port=8008, version=__version__)
    yield
    log.info("config_center.stopped")


app = FastAPI(title="Config Center", version=__version__, lifespan=lifespan)


# ============== Health ==============


@app.get("/config-center/health")
async def health() -> dict:
    """Config center health check."""
    namespaces = list_namespaces()
    items = list_items()
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "namespace_count": len(namespaces),
        "item_count": len(items),
    }


# ============== Namespaces ==============


@app.get("/config-center/namespaces", response_model=list[ConfigNamespace], tags=["配置命名空间"])
async def list_config_namespaces() -> list[ConfigNamespace]:
    """List all config namespaces."""
    return list_namespaces()


@app.post("/config-center/namespaces", status_code=201, tags=["配置命名空间"])
async def create_namespace(namespace: str, description: str = "") -> ConfigNamespace:
    """Create a new namespace."""
    return get_or_create_namespace(namespace, description)


# ============== Config Items ==============


@app.get("/config-center/configs", response_model=ConfigListResponse, tags=["配置项"])
async def list_configs(
    namespace: Optional[str] = None,
    status: Optional[str] = None,
) -> ConfigListResponse:
    """List config items, optionally filtered by namespace or status."""
    status_filter = ConfigStatus(status) if status else None
    items = list_items(namespace=namespace, status=status_filter)
    return ConfigListResponse(items=items, total=len(items), namespace=namespace)


@app.post("/config-center/configs", status_code=201, tags=["配置项"])
async def create_config(
    namespace: str,
    key: str,
    value,
    description: str = "",
    tags: Optional[dict] = None,
    created_by: str = "system",
) -> ConfigItem:
    """Create a new config item (in DRAFT status)."""
    get_or_create_namespace(namespace)
    item, created = set_item(
        namespace=namespace,
        key=key,
        value=value,
        description=description,
        tags=tags,
        created_by=created_by,
    )
    if not created:
        raise HTTPException(status_code=409, detail=f"Config '{namespace}/{key}' already exists")
    return item


@app.get("/config-center/configs/{namespace}/{key}", tags=["配置项"])
async def get_config(namespace: str, key: str) -> ConfigItem:
    """Get a specific config item."""
    item = get_item(namespace, key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Config '{namespace}/{key}' not found")
    return item


@app.put("/config-center/configs/{namespace}/{key}", tags=["配置项"])
async def update_config(
    namespace: str,
    key: str,
    value,
    description: Optional[str] = None,
    tags: Optional[dict] = None,
    created_by: str = "system",
) -> ConfigItem:
    """Update a config item (creates new draft version)."""
    existing = get_item(namespace, key)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Config '{namespace}/{key}' not found")
    item, _ = set_item(
        namespace=namespace,
        key=key,
        value=value,
        description=description or existing.description,
        tags=tags,
        created_by=created_by,
    )
    return item


@app.post("/config-center/configs/{namespace}/{key}/publish", tags=["配置项"])
async def publish_config(
    namespace: str,
    key: str,
    changed_by: str = "system",
    comment: str = "",
) -> ConfigItem:
    """Publish a config item (activate it and push to subscribers)."""
    item = publish_item(namespace, key, changed_by=changed_by, comment=comment)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Config '{namespace}/{key}' not found")
    # Push to subscribers asynchronously
    push_sync(item, ConfigChangeType.PUBLISHED.value)
    log.info("config.published", key=item.full_key(), version=item.version)
    return item


@app.delete("/config-center/configs/{namespace}/{key}", tags=["配置项"])
async def delete_config(namespace: str, key: str) -> dict:
    """Deprecate a config item."""
    item = deprecate_item(namespace, key)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Config '{namespace}/{key}' not found")
    push_sync(item, ConfigChangeType.DELETED.value)
    return {"namespace": namespace, "key": key, "deprecated": True}


# ============== Version History ==============


@app.get(
    "/config-center/configs/{namespace}/{key}/versions",
    response_model=ConfigVersionListResponse,
    tags=["版本历史"],
)
async def get_config_versions(namespace: str, key: str) -> ConfigVersionListResponse:
    """Get version history for a config item."""
    existing = get_item(namespace, key)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Config '{namespace}/{key}' not found")
    versions = get_versions(namespace, key)
    return ConfigVersionListResponse(key=key, namespace=namespace, versions=versions, total=len(versions))


@app.post("/config-center/configs/{namespace}/{key}/rollback", tags=["版本历史"])
async def rollback_config(
    namespace: str,
    key: str,
    target_version: int,
    changed_by: str = "system",
    comment: str = "",
) -> ConfigItem:
    """Rollback a config item to a specific version."""
    item = rollback_to_version(
        namespace,
        key,
        target_version=target_version,
        changed_by=changed_by,
        comment=comment,
    )
    if item is None:
        raise HTTPException(status_code=404, detail=f"Version {target_version} not found for '{namespace}/{key}'")
    push_sync(item, ConfigChangeType.ROLLED_BACK.value)
    return item


# ============== Audit Trail ==============


@app.get("/config-center/audit", tags=["审计"])
async def get_audit_log(
    namespace: Optional[str] = None,
    key: Optional[str] = None,
    limit: int = 100,
) -> dict:
    """Get the config change audit trail (newest first)."""
    changes = list_changes(namespace=namespace, key=key, limit=limit)
    return {"changes": changes, "total": len(changes)}


# ============== Subscribers ==============


@app.post("/config-center/subscribers", status_code=201, tags=["订阅者"])
async def register_subscriber_endpoint(req: SubscriberRegisterRequest) -> Subscriber:
    """Register a new subscriber for push notifications."""
    return register_subscriber(
        service_id=req.service_id,
        name=req.name,
        url=req.url,
        namespaces=req.namespaces,
    )


@app.get("/config-center/subscribers", tags=["订阅者"])
async def list_subscribers_endpoint(active: Optional[bool] = None) -> list[Subscriber]:
    """List all registered subscribers."""
    return list_subscribers(active=active)


@app.delete("/config-center/subscribers/{service_id}", tags=["订阅者"])
async def unregister_subscriber_endpoint(service_id: str) -> dict:
    """Unregister a subscriber."""
    ok = unregister_subscriber(service_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Subscriber '{service_id}' not found")
    return {"service_id": service_id, "unregistered": True}
