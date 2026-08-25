"""Module for the demo-hub demo.

Blueprint-aligned wiring: server configuration is bound from
``application.yaml`` via :func:`demo_hub.config.bind_web` — no literal
host/port/security values here.
"""

from __future__ import annotations

from dataclasses import replace

from demo_hub.config import bind_web
from demo_hub.controllers.api import HubApiController
from demo_hub.di.provider import HubProvider
from demo_hub.services.registry import ServiceRegistry
from demo_hub.ui.pages import HubPageController
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule


@module()
class DemoHubModule(Module):
    """Root module: hub console with embedded-fleet health checks."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        web_config = bind_web()
        if port is not None:  # programmatic override (tests/embedding)
            web_config = replace(
                web_config, server=replace(web_config.server, port=port)
            )
        return DynamicModule(
            module=cls,
            imports=[
                WebModule.configure(
                    controllers=[HubApiController, HubPageController],
                    web_config=web_config,
                ),
            ],
            providers=[HubProvider()],
            exports=[ServiceRegistry],
        )


__all__ = ["DemoHubModule"]
