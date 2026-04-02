"""Push notification service — notifies subscribers of config changes."""

from __future__ import annotations

import asyncio
import threading
from typing import List

import httpx

from apps.config_center.models import ConfigItem
from apps.config_center.store import list_subscribers, mark_notified
from common.tracing import get_logger

log = get_logger("config_center.push")

# Thread-safe async notification queue
_notification_queue: List[dict] = []
_queue_lock = threading.Lock()


async def _send_notification(subscriber_url: str, payload: dict) -> bool:
    """Send a notification to a subscriber. Returns True on success."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(subscriber_url, json=payload)
            return response.status_code in (200, 201, 202, 204)
    except Exception as e:
        log.warning("push.notification_failed", url=subscriber_url, error=str(e))
        return False


async def notify_subscribers(item: ConfigItem, change_type: str) -> dict:
    """Notify all relevant subscribers about a config change.

    Returns dict of {service_id: success}.
    """
    subscribers = list_subscribers(active=True)
    results = {}

    for sub in subscribers:
        # Filter by subscribed namespaces
        if sub.namespaces and item.namespace not in sub.namespaces:
            continue

        payload = {
            "type": "config_changed",
            "change_type": change_type,
            "key": item.full_key(),
            "namespace": item.namespace,
            "config": {
                "key": item.key,
                "namespace": item.namespace,
                "value": item.value,
                "version": item.version,
                "status": item.status,
            },
        }

        success = await _send_notification(sub.url, payload)
        results[sub.service_id] = success
        mark_notified(sub.service_id, success=success)

        log.info(
            "push.notification_sent",
            service_id=sub.service_id,
            key=item.full_key(),
            success=success,
        )

    return results


def push_sync(item: ConfigItem, change_type: str) -> dict:
    """Synchronously notify subscribers. Returns results dict."""
    return asyncio.run(notify_subscribers(item, change_type))


def enqueue_notification(item: ConfigItem, change_type: str) -> None:
    """Add notification to queue for background processing."""
    with _queue_lock:
        _notification_queue.append({"item": item, "change_type": change_type})


async def process_notification_queue() -> List[dict]:
    """Process all queued notifications. Returns list of results."""
    with _queue_lock:
        queue = list(_notification_queue)
        _notification_queue.clear()

    results = []
    for entry in queue:
        item = entry["item"]
        change_type = entry["change_type"]
        result = await notify_subscribers(item, change_type)
        results.append({"key": item.full_key(), "results": result})
    return results
