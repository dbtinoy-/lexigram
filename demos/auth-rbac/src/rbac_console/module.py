"""Module for the RBAC console demo."""

from __future__ import annotations

from dataclasses import replace

from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule
from rbac_console.config import bind_web
from rbac_console.controllers.api import RbacApiController
from rbac_console.di.provider import RbacProvider
from rbac_console.ui.pages import PagesController


@module()
class RbacModule(Module):
    """Root module: auth stack + permission-matrix console."""

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
                AuthModule.configure(),
                WebModule.configure(
                    controllers=[RbacApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            providers=[RbacProvider],
            exports=[],
        )


__all__ = ["RbacModule"]
