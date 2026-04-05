"""Configuration center in-memory store with version history and audit trail."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.config_center.models import (
    ConfigChange,
    ConfigChangeType,
    ConfigItem,
    ConfigNamespace,
    ConfigStatus,
    ConfigVersion,
    Subscriber,
)

# Global stores
_namespaces: Dict[str, ConfigNamespace] = {}
_items: Dict[str, ConfigItem] = {}  # key: "namespace/key"
_versions: Dict[str, List[ConfigVersion]] = {}  # key: "namespace/key"
_changes: List[ConfigChange] = []  # audit trail (in-memory, newest first)
_subscribers: Dict[str, Subscriber] = {}  # service_id -> Subscriber
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _item_key(namespace: str, key: str) -> str:
    return f"{namespace}/{key}"


# ============== Namespaces ==============


def get_or_create_namespace(namespace: str, description: str = "") -> ConfigNamespace:
    """Get or create a namespace."""
    global _namespaces
    with _lock:
        if namespace not in _namespaces:
            _namespaces[namespace] = ConfigNamespace(namespace=namespace, description=description)
        return _namespaces[namespace]


def list_namespaces() -> List[ConfigNamespace]:
    """List all namespaces."""
    with _lock:
        return [ns for ns in _namespaces.values()]


# ============== Config Items ==============


def get_item(namespace: str, key: str) -> Optional[ConfigItem]:
    """Get a config item by namespace and key."""
    with _lock:
        return _items.get(_item_key(namespace, key))


def list_items(namespace: Optional[str] = None, status: Optional[ConfigStatus] = None) -> List[ConfigItem]:
    """List config items, optionally filtered."""
    with _lock:
        result = [item for item in _items.values()]
    if namespace:
        result = [item for item in result if item.namespace == namespace]
    if status:
        result = [item for item in result if item.status == status]
    return result


def set_item(
    namespace: str,
    key: str,
    value: Any,
    description: str = "",
    tags: Optional[Dict[str, str]] = None,
    created_by: str = "system",
) -> tuple[ConfigItem, bool]:
    """Create or update a config item (keeps in draft). Returns (item, created)."""
    item_key = _item_key(namespace, key)
    with _lock:
        is_new = item_key not in _items
        old_item = _items.get(item_key)

        if is_new:
            item = ConfigItem(
                namespace=namespace,
                key=key,
                value=value,
                description=description,
                status=ConfigStatus.DRAFT,
                version=1,
                created_by=created_by,
                tags=tags or {},
            )
        else:
            assert old_item is not None
            item = old_item.model_copy()
            item.value = value
            if description:
                item.description = description
            if tags is not None:
                item.tags = tags
            item.updated_at = _now()
            item.version += 1

        _items[item_key] = item

        # Record version snapshot
        if item_key not in _versions:
            _versions[item_key] = []
        _versions[item_key].append(
            ConfigVersion(
                key=key,
                namespace=namespace,
                version=item.version,
                value=value,
                status=item.status,
                changed_by=created_by,
                changed_at=_now(),
                change_type=ConfigChangeType.CREATED if is_new else ConfigChangeType.UPDATED,
            )
        )

        # Audit trail
        _changes.insert(
            0,
            ConfigChange(
                key=key,
                namespace=namespace,
                version=item.version,
                change_type=ConfigChangeType.CREATED if is_new else ConfigChangeType.UPDATED,
                changed_by=created_by,
                changed_at=_now(),
                old_value=old_item.value if old_item else None,
                new_value=value,
            ),
        )

        return item, is_new


def publish_item(namespace: str, key: str, changed_by: str = "system", comment: str = "") -> Optional[ConfigItem]:
    """Publish a config item (activate it). Returns updated item or None."""
    item_key = _item_key(namespace, key)
    with _lock:
        item = _items.get(item_key)
        if item is None:
            return None

        item = item.model_copy()
        item.status = ConfigStatus.PUBLISHED
        item.published_at = _now()
        item.updated_at = _now()
        _items[item_key] = item

        # Record version snapshot
        _versions[item_key].append(
            ConfigVersion(
                key=key,
                namespace=namespace,
                version=item.version,
                value=item.value,
                status=item.status,
                changed_by=changed_by,
                changed_at=_now(),
                change_type=ConfigChangeType.PUBLISHED,
                comment=comment,
            )
        )

        # Audit trail
        _changes.insert(
            0,
            ConfigChange(
                key=key,
                namespace=namespace,
                version=item.version,
                change_type=ConfigChangeType.PUBLISHED,
                changed_by=changed_by,
                changed_at=_now(),
                new_value=item.value,
                comment=comment,
            ),
        )
        return item


def deprecate_item(namespace: str, key: str, changed_by: str = "system") -> Optional[ConfigItem]:
    """Mark a config item as deprecated. Returns updated item or None."""
    item_key = _item_key(namespace, key)
    with _lock:
        item = _items.get(item_key)
        if item is None:
            return None
        item = item.model_copy()
        item.status = ConfigStatus.DEPRECATED
        item.updated_at = _now()
        _items[item_key] = item

        _changes.insert(
            0,
            ConfigChange(
                key=key,
                namespace=namespace,
                version=item.version,
                change_type=ConfigChangeType.DELETED,
                changed_by=changed_by,
                changed_at=_now(),
                old_value=item.value,
            ),
        )
        return item


# ============== Version History ==============


def get_versions(namespace: str, key: str) -> List[ConfigVersion]:
    """Get version history for a config item."""
    item_key = _item_key(namespace, key)
    with _lock:
        return list(reversed(_versions.get(item_key, [])))


def rollback_to_version(
    namespace: str,
    key: str,
    target_version: int,
    changed_by: str = "system",
    comment: str = "",
) -> Optional[ConfigItem]:
    """Rollback to a specific version. Returns new current item or None."""
    item_key = _item_key(namespace, key)
    with _lock:
        versions = _versions.get(item_key, [])
        target = next((v for v in versions if v.version == target_version), None)
        if target is None:
            return None

        item = _items.get(item_key)
        old_value = item.value if item else None

        # Create new version from rollback target
        new_item = ConfigItem(
            namespace=namespace,
            key=key,
            value=target.value,
            description="",
            status=ConfigStatus.PUBLISHED,
            version=(item.version + 1) if item else 1,
            created_by=changed_by,
            published_at=_now(),
        )
        _items[item_key] = new_item

        _versions[item_key].append(
            ConfigVersion(
                key=key,
                namespace=namespace,
                version=new_item.version,
                value=target.value,
                status=new_item.status,
                changed_by=changed_by,
                changed_at=_now(),
                change_type=ConfigChangeType.ROLLED_BACK,
                comment=f"Rolled back to v{target_version}: {comment}",
            )
        )

        _changes.insert(
            0,
            ConfigChange(
                key=key,
                namespace=namespace,
                version=new_item.version,
                change_type=ConfigChangeType.ROLLED_BACK,
                changed_by=changed_by,
                changed_at=_now(),
                old_value=old_value,
                new_value=target.value,
                comment=comment,
            ),
        )
        return new_item


# ============== Audit Trail ==============


def list_changes(
    namespace: Optional[str] = None,
    key: Optional[str] = None,
    limit: int = 100,
) -> List[ConfigChange]:
    """List config changes (audit trail), newest first."""
    with _lock:
        result = list(_changes)
    if namespace:
        result = [c for c in result if c.namespace == namespace]
    if key:
        result = [c for c in result if c.key == key]
    return result[:limit]


# ============== Subscribers ==============


def register_subscriber(
    service_id: str,
    name: str,
    url: str,
    namespaces: Optional[List[str]] = None,
) -> Subscriber:
    """Register a subscriber for push notifications."""
    sub = Subscriber(
        service_id=service_id,
        name=name,
        url=url,
        namespaces=namespaces or [],
    )
    with _lock:
        _subscribers[service_id] = sub
    return sub


def get_subscriber(service_id: str) -> Optional[Subscriber]:
    """Get a subscriber by service_id."""
    with _lock:
        return _subscribers.get(service_id)


def list_subscribers(active: Optional[bool] = None) -> List[Subscriber]:
    """List all subscribers."""
    with _lock:
        result = [s for s in _subscribers.values()]
    if active is not None:
        result = [s for s in result if s.active == active]
    return result


def unregister_subscriber(service_id: str) -> bool:
    """Unregister a subscriber. Returns True if found."""
    with _lock:
        if service_id in _subscribers:
            del _subscribers[service_id]
            return True
    return False


def mark_notified(service_id: str, success: bool = True) -> None:
    """Update last_notified_at and optionally last_success_at."""
    with _lock:
        sub = _subscribers.get(service_id)
        if sub:
            sub.last_notified_at = _now()
            if success:
                sub.last_success_at = _now()


# ============== Seed ==============


def seed_defaults() -> None:
    """Seed default namespaces and config items."""
    # Namespaces
    get_or_create_namespace("feature_flags", "Feature toggle flags")
    get_or_create_namespace("model_routing", "Model routing and fallback strategies")
    get_or_create_namespace("alerting", "Alerting thresholds and channels")

    # Default config items (published)
    set_item(
        namespace="feature_flags",
        key="dark_mode",
        value=False,
        description="Enable dark mode UI",
        created_by="system",
    )
    publish_item("feature_flags", "dark_mode", changed_by="system", comment="Initial seed")

    set_item(
        namespace="feature_flags",
        key="enable_rag",
        value=True,
        description="Enable RAG knowledge enrichment",
        created_by="system",
    )
    publish_item("feature_flags", "enable_rag", changed_by="system", comment="Initial seed")

    set_item(
        namespace="model_routing",
        key="planning_model",
        value="minimax-cn/MiniMax-M2.7",
        description="Default model for planning tasks",
        created_by="system",
    )
    publish_item("model_routing", "planning_model", changed_by="system", comment="Initial seed")

    set_item(
        namespace="alerting",
        key="error_rate_threshold",
        value=0.05,
        description="Error rate threshold for alerts (5%)",
        created_by="system",
    )
    publish_item("alerting", "error_rate_threshold", changed_by="system", comment="Initial seed")
