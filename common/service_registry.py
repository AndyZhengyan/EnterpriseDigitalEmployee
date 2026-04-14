"""Service Registry — single source of truth for all hub/service URLs.

Architecture principle: all hub URLs are defined here. Individual apps and
modules must NOT hardcode host:port strings; they must call
`get_hub_url(name)` or `get_service_url(name)`.

Environment variable overrides
-------------------------------
Every service entry can be overridden at runtime by setting the matching
`{SERVICE_NAME}_URL` env var (e.g. `MODEL_HUB_URL=http://192.168.1.10:9000`).
When the env var is present and non-empty it wins over the config default.

Usage
-----
    from common.service_registry import get_hub_url

    url = get_hub_url("model_hub")          # → "http://127.0.0.1:8002"
    url = get_hub_url("model_hub", path="/v1/chat")  # → "http://127.0.0.1:8002/v1/chat"
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

# ── Dataclass definitions ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class HubEntry:
    """A single hub service entry."""

    name: str  # internal key, e.g. "model_hub"
    default_host: str
    default_port: int
    scheme: str = "http"
    description: str = ""

    @property
    def default_url(self) -> str:
        return f"{self.scheme}://{self.default_host}:{self.default_port}"

    def url(self, *, path: Optional[str] = None, https: bool = False) -> str:
        """Return the URL, honouring any matching env-var override.

        Env var format: `{NAME}_URL` (e.g. `MODEL_HUB_URL`).
        """
        base = self._resolve_base(https=https)
        if path:
            # Normalise: ensure single leading "/" and no trailing "/"
            path = "/" + path.strip("/")
        return f"{base}{path}" if path else base

    def _resolve_base(self, *, https: bool = False) -> str:
        """Return base URL, checking env override first."""
        env_key = f"{self.name.upper()}_URL"
        env_val = os.environ.get(env_key)
        if env_val:
            # Strip trailing path if any — caller can re-add via `path=`
            return env_val.rstrip("/")
        scheme = "https" if https else self.scheme
        return f"{scheme}://{self.default_host}:{self.default_port}"


# ── Registry ───────────────────────────────────────────────────────────────────

_HUB_ENTRIES: dict[str, HubEntry] = {
    # Internal micro-services
    "model_hub": HubEntry(
        name="model_hub",
        default_host="127.0.0.1",
        default_port=8002,
        description="LLM gateway / model routing hub",
    ),
    "skill_hub": HubEntry(
        name="skill_hub",
        default_host="127.0.0.1",
        default_port=8004,
        description="Skill registry and execution hub",
    ),
    "connector_hub": HubEntry(
        name="connector_hub",
        default_host="127.0.0.1",
        default_port=8003,
        description="External system connector hub",
    ),
    "knowledge_hub": HubEntry(
        name="knowledge_hub",
        default_host="127.0.0.1",
        default_port=8005,
        description="Knowledge-base / RAG hub",
    ),
    # Platform services
    "runtime": HubEntry(
        name="runtime",
        default_host="127.0.0.1",
        default_port=8001,
        description="Runtime executor service",
    ),
    "gateway": HubEntry(
        name="gateway",
        default_host="127.0.0.1",
        default_port=18789,
        description="OpenClaw Gateway (pi-agent control plane)",
    ),
}


# ── Public API ─────────────────────────────────────────────────────────────────


def get_hub_url(
    name: str,
    *,
    path: Optional[str] = None,
    https: bool = False,
) -> str:
    """Return the full URL for a registered hub/service.

    Priority:
      1. `{NAME}_URL` env var (if set and non-empty)
      2. Configured default (host:port from registry)

    Args:
        name:   Service key from the registry (e.g. "model_hub").
        path:   Optional path segment to append (e.g. "/v1/chat").
        https:  Force https scheme; useful for production deployments.

    Returns:
        Fully-qualified URL string.

    Raises:
        KeyError: if `name` is not registered.
    """
    entry = _HUB_ENTRIES[name]
    return entry.url(path=path, https=https)


def get_hub_entry(name: str) -> HubEntry:
    """Return the HubEntry dataclass for a given service name."""
    return _HUB_ENTRIES[name]


def all_hub_entries() -> dict[str, HubEntry]:
    """Return a shallow copy of the full registry."""
    return dict(_HUB_ENTRIES)
