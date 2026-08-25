"""Module for the MFA console demo.

Blueprint-aligned wiring: web and auth configuration come from
``application.yaml`` — ``AuthModule.configure()`` is called without an
explicit config so the auth provider receives its section via framework
injection (the application boots with this demo's ``LexigramConfig``).
"""

from __future__ import annotations

from dataclasses import replace

from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule
from mfa_console.config import bind_web
from mfa_console.controllers.api import MfaApiController
from mfa_console.di.provider import MfaProvider
from mfa_console.ui.pages import PagesController


@module()
class MfaModule(Module):
    """Root module: auth stack + TOTP challenge console."""

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
                    controllers=[MfaApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            # Intentionally private: a leaf console exports nothing.
            providers=[MfaProvider()],
        )


__all__ = ["MfaModule"]
