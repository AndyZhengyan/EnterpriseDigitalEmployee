"""Configuration center data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConfigStatus(str, Enum):
    """Config item lifecycle status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ConfigChangeType(str, Enum):
    """Type of configuration change."""

    CREATED = "created"
    UPDATED = "updated"
    PUBLISHED = "published"
    DELETED = "deleted"
    ROLLED_BACK = "rolled_back"


class ConfigNamespace(BaseModel):
    """Logical grouping for config items."""

    namespace: str  # e.g. "feature_flags", "model_routing", "alerting"
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "ignore"}


class ConfigItem(BaseModel):
    """A single configuration item."""

    key: str  # namespace/key, e.g. "feature_flags.dark_mode"
    namespace: str
    value: Any  # JSON-serializable value
    description: str = ""
    status: ConfigStatus = ConfigStatus.DRAFT
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
    created_by: str = "system"
    tags: Dict[str, str] = Field(default_factory=dict)

    model_config = {"use_enum_values": True, "extra": "ignore"}

    def full_key(self) -> str:
        return f"{self.namespace}/{self.key}"


class ConfigVersion(BaseModel):
    """A historical snapshot of a config item."""

    key: str
    namespace: str
    version: int
    value: Any
    status: ConfigStatus
    changed_by: str
    changed_at: datetime
    change_type: ConfigChangeType
    comment: str = ""

    model_config = {"use_enum_values": True, "extra": "ignore"}


class ConfigChange(BaseModel):
    """A single config change event for audit trail."""

    key: str
    namespace: str
    version: int
    change_type: ConfigChangeType
    changed_by: str
    changed_at: datetime
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    comment: str = ""

    model_config = {"use_enum_values": True, "extra": "ignore"}


class Subscriber(BaseModel):
    """A service that subscribes to config change notifications."""

    service_id: str  # e.g. "model-hub", "runtime"
    name: str
    url: str  # HTTP callback URL
    namespaces: List[str] = Field(default_factory=list)  # subscribed namespaces, empty = all
    active: bool = True
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_notified_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None

    model_config = {"extra": "ignore"}


# ============== Request/Response ==============


class ConfigCreateRequest(BaseModel):
    """Create a new config item."""

    namespace: str
    key: str
    value: Any
    description: str = ""
    tags: Dict[str, str] = Field(default_factory=dict)
    created_by: str = "system"


class ConfigUpdateRequest(BaseModel):
    """Update an existing config item (keeps in draft)."""

    value: Optional[Any] = None
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    comment: str = ""


class ConfigPublishRequest(BaseModel):
    """Publish a config item (activate it)."""

    comment: str = ""


class ConfigRollbackRequest(BaseModel):
    """Rollback to a specific version."""

    target_version: int
    comment: str = ""


class ConfigListResponse(BaseModel):
    """List config items."""

    items: List[ConfigItem]
    total: int
    namespace: Optional[str] = None


class ConfigVersionListResponse(BaseModel):
    """List version history for a config item."""

    key: str
    namespace: str
    versions: List[ConfigVersion]
    total: int


class SubscriberRegisterRequest(BaseModel):
    """Register a new subscriber."""

    service_id: str
    name: str
    url: str
    namespaces: List[str] = Field(default_factory=list)
