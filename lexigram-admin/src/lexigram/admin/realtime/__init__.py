"""Real-time communication module for lexigram-admin.

Provides SSE and WebSocket handlers for real-time updates.
"""

from __future__ import annotations

from lexigram.admin.realtime.sse import (
    HAS_SSE,
    AdminEvent,
    AdminEventType,
    BulkOperationProgressHandler,
)
from lexigram.admin.realtime.subject_hub import SubjectAdminEventHub
from lexigram.admin.realtime.websocket import (
    HAS_WEBSOCKET,
    AdminWebSocketHandler,
    AdminWebSocketManager,
    ResourceChangeNotifier,
    WSMessage,
    WSMessageType,
)

__all__ = [
    "HAS_SSE",
    "HAS_WEBSOCKET",
    "AdminEvent",
    "AdminEventType",
    "AdminWebSocketHandler",
    "AdminWebSocketManager",
    "BulkOperationProgressHandler",
    "ResourceChangeNotifier",
    "SubjectAdminEventHub",
    "WSMessage",
    "WSMessageType",
]
