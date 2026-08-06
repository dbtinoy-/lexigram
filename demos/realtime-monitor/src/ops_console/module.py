"""Realtime monitor demo module.

Wires the web layer (dashboard, SSE, HTTP publish) together with the realtime
provider (shared event stream, WS operator channel, heartbeat producer).
"""

from __future__ import annotations

import os

from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule
from lexigram.web.di.provider import WebProvider
from ops_console.controllers.console import ConsoleController, EventsStreamHandler
from ops_console.controllers.operator import OperatorHandler
from ops_console.di.provider import RealtimeProvider
from ops_console.services.event_stream import EventStreamService


@module()
class RealtimeModule(Module):
    """Root module for the realtime monitor demo."""

    @classmethod
    def configure(
        cls,
        port: int | None = None,
        heartbeat_interval: float = 15.0,
    ) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("REALTIME_PORT", "7071"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                WebModule.configure(
                    controllers=[ConsoleController],
                    port=selected_port,
                ),
            ],
            providers=[RealtimeProvider(heartbeat_interval=heartbeat_interval)],
            exports=[
                EventStreamService,
                EventsStreamHandler,
                OperatorHandler,
                ConsoleController,
                WebProvider,
            ],
        )


__all__ = ["RealtimeModule"]
