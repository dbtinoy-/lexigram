"""Real-time communication module for lexigram-admin.

Provides SSE and WebSocket handlers for real-time updates.
"""

from __future__ import annotations

from lexigram.admin.realtime.sse import (
    HAS_SSE,
    AdminEvent,
    AdminEventHub,
    AdminEventsHandler,
    AdminEventType,
    BulkOperationProgressHandler,
    create_sse_response,
)
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
    "AdminEventHub",
    "AdminEventType",
    "AdminEventsHandler",
    "AdminWebSocketHandler",
    "AdminWebSocketManager",
    "BulkOperationProgressHandler",
    "ResourceChangeNotifier",
    "WSMessage",
    "WSMessageType",
    "create_sse_response",
]
