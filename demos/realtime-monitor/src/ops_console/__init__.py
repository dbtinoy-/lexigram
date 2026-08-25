"""Realtime monitor demo application package."""

from __future__ import annotations

from ops_console.app import create_app
from ops_console.controllers.api import ConsoleController, EventsStreamHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService, StreamStats

__all__ = [
    "ConsoleController",
    "EventStreamService",
    "EventsStreamHandler",
    "Severity",
    "StreamStats",
    "SystemEvent",
    "create_app",
]
