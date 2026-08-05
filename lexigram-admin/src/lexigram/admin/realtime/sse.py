"""Server-Sent Events (SSE) integration for lexigram-admin.

This module provides SSE handlers for real-time updates in admin.

FWK-10: SSE for real-time updates using @sse_endpoint.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ============================================================================
# Protocols for optional web integration
# ============================================================================

# Placeholder types for when lexigram-web is not available
# These are replaced via container registration when lexigram-web is present


class SSEHandler:
    """Base SSE handler class.

    This is a local implementation that does not depend on lexigram-web.
    When lexigram-web is available, its SSEHandler is registered in the container
    and resolved through IoC.
    """

    async def stream(self) -> AsyncGenerator[dict[str, Any], None]:
        """Yield SSE events as dictionaries."""
        if False:  # pragma: no cover
            yield {}
        return


# ============================================================================
# Event Types
# ============================================================================


class AdminEventType(StrEnum):
    """Standard admin event types."""

    # Resource events
    RESOURCE_CREATED = "resource.created"
    RESOURCE_UPDATED = "resource.updated"
    RESOURCE_DELETED = "resource.deleted"

    # Bulk operation events
    BULK_PROGRESS = "bulk.progress"
    BULK_COMPLETED = "bulk.completed"
    BULK_FAILED = "bulk.failed"

    # Notification events
    NOTIFICATION = "notification"
    TOAST = "toast"

    # System events
    HEARTBEAT = "heartbeat"
    RECONNECT = "reconnect"


@dataclass
class AdminEvent:
    """Admin SSE event."""

    event_type: AdminEventType | str
    data: dict[str, Any]
    id: str | None = None
    resource_type: str | None = None
    resource_id: Any = None
    tenant_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SSE."""
        return {
            "event": str(
                self.event_type.value
                if isinstance(self.event_type, AdminEventType)
                else self.event_type,
            ),
            "data": {
                **self.data,
                "timestamp": self.timestamp.isoformat(),
                "resource_type": self.resource_type,
                "resource_id": self.resource_id,
            },
            "id": self.id,
        }


HAS_SSE = True  # local placeholder is always available

# ============================================================================
# Bulk Operation Progress Handler
# ============================================================================


class BulkOperationProgressHandler(SSEHandler if HAS_SSE else object):  # type: ignore[misc]
    """SSE handler for bulk operation progress.

    Streams progress updates for long-running bulk operations.

    Usage:
        >>> @sse_endpoint("/admin/bulk/{operation_id}/progress")
        ... class BulkProgressEndpoint(BulkOperationProgressHandler):
        ...     pass
    """

    heartbeat_interval: int = 5
    retry: int = 1000

    # In-memory progress tracking (should be Redis-backed in production)
    _progress: dict[str, dict[str, Any]] = {}

    @classmethod
    def start_operation(
        cls,
        operation_id: str,
        total: int,
        description: str = "",
    ) -> None:
        """Start tracking a new operation."""
        cls._progress[operation_id] = {
            "total": total,
            "processed": 0,
            "failed": 0,
            "description": description,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
        }

    @classmethod
    def update_progress(
        cls,
        operation_id: str,
        processed: int,
        failed: int = 0,
    ) -> None:
        """Update operation progress."""
        if operation_id in cls._progress:
            cls._progress[operation_id]["processed"] = processed
            cls._progress[operation_id]["failed"] = failed

    @classmethod
    def complete_operation(
        cls,
        operation_id: str,
        success: bool = True,
        message: str = "",
    ) -> None:
        """Mark operation as complete."""
        if operation_id in cls._progress:
            cls._progress[operation_id]["status"] = "completed" if success else "failed"
            cls._progress[operation_id]["message"] = message
            cls._progress[operation_id]["completed_at"] = datetime.now(
                UTC,
            ).isoformat()

    async def stream(self, request: Any) -> AsyncGenerator[dict[str, Any], None]:
        """Stream progress for an operation."""
        operation_id = ""
        if hasattr(request, "path_params"):
            operation_id = request.path_params.get("operation_id", "")

        if not operation_id or operation_id not in self._progress:
            yield {
                "event": "error",
                "data": {"message": "Operation not found"},
            }
            return

        while True:
            progress = self._progress.get(operation_id)
            if not progress:
                break

            yield {
                "event": "progress",
                "data": progress,
            }

            if progress["status"] in ("completed", "failed"):
                # Final event
                yield {
                    "event": progress["status"],
                    "data": progress,
                }
                # Cleanup
                self._progress.pop(operation_id, None)
                break

            await asyncio.sleep(0.5)



__all__ = [
    # Flags
    "HAS_SSE",
    "AdminEvent",
    # Event types
    "AdminEventType",
    # Handlers
    "BulkOperationProgressHandler",
]

