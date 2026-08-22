"""Module for the RBAC console demo."""

from __future__ import annotations

import os

from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.auth.module import AuthModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from rbac_console.controllers.api import RbacApiController
from rbac_console.di.provider import RbacProvider
from rbac_console.ui.pages import PagesController


def build_auth_config() -> AuthConfig:
    """Offline demo config: explicit dev secret.

    Note:
        Users and roles are seeded at boot by ``RbacProvider`` because
        ``AuthConfig.users`` / ``AuthConfig.roles`` are inert today.
    """
    secret = "rbac-console-demo-secret-key-0123456789ab"
    return AuthConfig(
        secret_key=secret,
        token=JWTConfig(secret_key=secret),
    )


@module()
class RbacModule(Module):
    """Root module: auth stack + permission-matrix console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("RBAC_PORT", "8090"))
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
                    controllers=[RbacApiController, PagesController],
                    web_config=web_config,
                ),
            ],
            providers=[RbacProvider],
            exports=[],
        )


__all__ = ["RbacModule"]
