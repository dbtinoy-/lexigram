"""Module for the auth web demo."""

from __future__ import annotations

import os

from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig

from auth_web.controllers.api import AuthApiController
from auth_web.ui.pages import PagesController
from auth_web.di.provider import AuthWebProvider, build_auth_config


@module()
class AuthWebModule(Module):
    """Root module: auth stack + account-lifecycle UI."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("AUTH_WEB_PORT", "8081"))
        )
        web_config = WebConfig(
            server=ServerConfig(host="127.0.0.1", port=selected_port),
            # The demo posts plain JSON over local http; no browser
            # synchronizer token needed (matches realtime-monitor).
            security=SecurityConfig(enable_csrf=False),
        )
        return DynamicModule(
            module=cls,
            imports=[
                AuthModule.configure(build_auth_config()),
                WebModule.configure(
                    controllers=[AuthApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            providers=[AuthWebProvider],
            exports=[],
        )


__all__ = ["AuthWebModule"]
