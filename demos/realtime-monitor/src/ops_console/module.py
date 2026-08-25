"""Realtime monitor demo module.

Blueprint-aligned wiring: configuration is bound from ``application.yaml``
via :func:`ops_console.config.bind_application` — no literal host/port/security
values here. Wires the web layer (dashboard, SSE, HTTP publish) together with
the realtime provider (shared event stream, WS operator channel, heartbeat).
"""

from __future__ import annotations

from dataclasses import replace

from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule
from ops_console.config import bind_application
from ops_console.controllers.api import ConsoleController
from ops_console.controllers.operator import OperatorHandler
from ops_console.di.provider import RealtimeProvider
from ops_console.services.event_stream import EventStreamService
from ops_console.ui.pages import PagesController


@module()
class RealtimeModule(Module):
    """Root module for the realtime monitor demo."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        web_config, demo_config = bind_application()
        if port is not None:  # embedded-hub override; children never serve
            web_config = replace(
                web_config, server=replace(web_config.server, port=port)
            )
        return DynamicModule(
            module=cls,
            imports=[
                WebModule.configure(
                    controllers=[ConsoleController, OperatorHandler, PagesController],
                    web_config=web_config,
                ),
            ],
            providers=[RealtimeProvider(config=demo_config)],
            exports=[EventStreamService],
        )


__all__ = ["RealtimeModule"]
