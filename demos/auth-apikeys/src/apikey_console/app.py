"""Application composition root for the auth-apikeys demo."""

from __future__ import annotations

from apikey_console.controllers.api import KeysApiController
from apikey_console.di.provider import ApiKeysProvider
from apikey_console.ui.pages import PagesController
from lexigram.app.base import Application
from lexigram.auth.config import AuthConfig
from lexigram.auth.module import AuthModule
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def _coerce_auth_config(auth_config: AuthConfig) -> AuthConfig:
    """Normalize nested sections that can load as raw dicts."""
    token = getattr(auth_config, "token", None)
    if isinstance(token, dict):
        from lexigram.auth.config import JWTConfig

        return auth_config.model_copy(update={"token": JWTConfig(**token)}, deep=True)
    return auth_config


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) application."""
    config = config or LexigramConfig.from_yaml()
    auth_config = _coerce_auth_config(config.get_section("auth", AuthConfig))
    web_config = config.get_section("web", WebConfig)

    app = Application(name="apikeys-console", config=config)
    app.add_modules(
        [
            AuthModule.configure(config=auth_config),
            WebModule.configure(
                web_config=web_config,
                controllers=[KeysApiController, PagesController],
            ),
        ]
    )
    app.add_provider(ApiKeysProvider())
    return app


__all__ = ["create_app"]
