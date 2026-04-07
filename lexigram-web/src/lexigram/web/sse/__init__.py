"""Server-Sent Events support for Lexigram Web."""

from __future__ import annotations

from lexigram.web.sse.backpressure import (
    SSEBackpressureHandler,
    SSEConnectionEvents,
    SSEResponse,
    SSERetryTracker,
)
from lexigram.web.sse.decorators import sse_endpoint
from lexigram.web.sse.handler import AbstractSSEHandler
from lexigram.web.sse.heartbeat import SSEHeartbeatScheduler, get_heartbeat_scheduler
from lexigram.web.transport.sse import EventSourceResponse, ServerSentEvent

__all__ = [
    "AbstractSSEHandler",
    "EventSourceResponse",
    "SSEBackpressureHandler",
    "SSEConnectionEvents",
    "SSEHeartbeatScheduler",
    "SSEResponse",
    "SSERetryTracker",
    "ServerSentEvent",
    "get_heartbeat_scheduler",
    "sse_endpoint",
]
