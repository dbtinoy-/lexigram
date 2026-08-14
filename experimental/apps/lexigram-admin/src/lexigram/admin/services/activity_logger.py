"""Activity logging service for admin user actions."""

from __future__ import annotations

import contextvars
from datetime import UTC, datetime
from typing import Any

from lexigram.di.decorators import inject
from lexigram.logging import get_logger

# Request-scoped in-memory dict, isolated per async context.
# Populated externally (e.g. by admin middleware) when user context is available.
_request_cache_var: contextvars.ContextVar[dict[str, Any] | None] = (
    contextvars.ContextVar(
        "admin_request_cache",
        default=None,
    )
)


def get_request_cache() -> dict[str, Any]:
    """Return the request-scoped cache dict for the current async context."""
    cache = _request_cache_var.get()
    return cache if cache is not None else {}


logger = get_logger(__name__)


@inject
class ActivityLogger:
    """Service for tracking and retrieving admin user activity."""

    def __init__(self, capacity: int = 1000):
        self._capacity = capacity
        self._activities: list[dict[str, Any]] = []

    def log(
        self,
        action: str,
        resource: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Log an admin activity.

        This captures context from the current request if available.
        """
        request_cache = get_request_cache()
        user_id = request_cache.get("user_id", "system")

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "details": details or {},
            "success": success,
            "error": error,
        }

        # Append to in-memory list (last N activities)
        self._activities.append(entry)
        if len(self._activities) > self._capacity:
            self._activities.pop(0)

        # Also log to standard logger
        log_msg = f"Admin Action: {action} on {resource}/{resource_id} by {user_id} - {'Success' if success else 'Failed'}"
        if error:
            log_msg += f": {error}"
        logger.info(log_msg)

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent activities."""
        return self._activities[-limit:]

    def clear(self) -> None:
        """Clear the activity history."""
        self._activities.clear()


_instance: ActivityLogger | None = None


def get_activity_logger() -> ActivityLogger:
    """Get global activity logger singleton."""
    global _instance
    if _instance is None:
        _instance = ActivityLogger()
    return _instance
