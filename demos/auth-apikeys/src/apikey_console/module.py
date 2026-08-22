"""Module for the API-keys console demo."""

from __future__ import annotations

import os

from apikey_console.controllers.api import KeysApiController
from apikey_console.controllers.pages import PagesController
from apikey_console.di.provider import ApiKeysProvider, build_auth_config
from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig


@module()
class ApiKeysModule(Module):
    """Root module: auth stack + API-key management console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("APIKEYS_PORT", "8084"))
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
                    controllers=[KeysApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            providers=[ApiKeysProvider],
            exports=[],
        )


__all__ = ["ApiKeysModule"]
