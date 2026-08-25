"""Module for the API-keys console demo.

Blueprint-aligned wiring: web and auth configuration come from
``application.yaml`` — ``AuthModule.configure()`` is called without an
explicit config so the auth provider receives its section via framework
injection (the application boots with this demo's ``LexigramConfig``).
"""

from __future__ import annotations

from dataclasses import replace

from apikey_console.config import bind_web
from apikey_console.controllers.api import KeysApiController
from apikey_console.controllers.pages import PagesController
from apikey_console.di.provider import ApiKeysProvider
from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule


@module()
class ApiKeysModule(Module):
    """Root module: auth stack + API-key management console."""

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
                    controllers=[KeysApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            # Intentionally private: a leaf console exports nothing.
            providers=[ApiKeysProvider()],
        )


__all__ = ["ApiKeysModule"]
