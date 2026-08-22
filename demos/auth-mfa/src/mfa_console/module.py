"""Module for the MFA console demo."""

from __future__ import annotations

import os

from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from mfa_console.controllers.api import MfaApiController
from mfa_console.di.provider import MfaProvider, build_auth_config
from mfa_console.ui.pages import PagesController


@module()
class MfaModule(Module):
    """Root module: auth stack + TOTP challenge console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("MFA_PORT", "8092"))
        )
        web_config = WebConfig(
            server=ServerConfig(host="127.0.0.1", port=selected_port),
            # Plain JSON posts over local http; no synchronizer token needed.
            security=SecurityConfig(enable_csrf=False),
        )
        return DynamicModule(
            module=cls,
            imports=[
                AuthModule.configure(build_auth_config()),
                WebModule.configure(
                    controllers=[MfaApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            providers=[MfaProvider],
            exports=[],
        )


__all__ = ["MfaModule"]
