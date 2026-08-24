"""Module for the demo-hub demo."""

from __future__ import annotations

import os

from demo_hub.controllers.api import HubApiController
from demo_hub.di.provider import HubProvider
from demo_hub.services.registry import ServiceRegistry
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig


@module()
class DemoHubModule(Module):
    """Root module: hub console with live service health checks."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("DEMO_HUB_PORT", "7000"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                WebModule.configure(
                    controllers=[HubApiController],
                    web_config=WebConfig(
                        server=ServerConfig(
                            host="127.0.0.1",
                            port=selected_port,
                        ),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[HubProvider],
            exports=[ServiceRegistry],
        )


__all__ = ["DemoHubModule"]
