"""Realtime monitor demo module.

Wires the web layer (dashboard, SSE, HTTP publish) together with the realtime
provider (shared event stream, WS operator channel, heartbeat producer).
"""

from __future__ import annotations

import os

from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.di.provider import WebProvider
from lexigram.web.security import SecurityConfig
from ops_console.controllers.api import ConsoleController, EventsStreamHandler
from ops_console.controllers.operator import OperatorHandler
from ops_console.di.provider import RealtimeProvider
from ops_console.services.event_stream import EventStreamService
from ops_console.ui.pages import PagesController


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
        web_config = WebConfig(
            server=ServerConfig(host="127.0.0.1", port=selected_port),
            # The demo's publish endpoint is meant to accept events from
            # external tools (curl, operator scripts) — protect it with a
            # plain check instead of a browser synchronizer token.
            security=SecurityConfig(enable_csrf=False),
        )
        return DynamicModule(
            module=cls,
            imports=[
                WebModule.configure(
                    controllers=[ConsoleController, OperatorHandler, PagesController],
                    web_config=web_config,
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
