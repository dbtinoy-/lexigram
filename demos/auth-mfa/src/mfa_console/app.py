"""Application composition root for the auth-mfa demo."""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.auth.config import AuthConfig
from lexigram.auth.module import AuthModule
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from mfa_console.config import load_lex_config
from mfa_console.controllers.api import MfaApiController
from mfa_console.di.provider import MfaProvider
from mfa_console.ui.pages import PagesController


def _coerce_auth_config(auth_config: AuthConfig) -> AuthConfig:
    """Normalize nested sections that can load as raw dicts."""
    token = getattr(auth_config, "token", None)
    if isinstance(token, dict):
        from lexigram.auth.config import JWTConfig

        return auth_config.model_copy(update={"token": JWTConfig(**token)}, deep=True)
    return auth_config


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) application."""
    config = config or load_lex_config()
    auth_config = _coerce_auth_config(config.get_section("auth", AuthConfig))
    web_config = config.get_section("web", WebConfig)

    app = Application(name="mfa-console", config=config)
    app.add_modules(
        [
            AuthModule.configure(config=auth_config),
            WebModule.configure(
                web_config=web_config,
                controllers=[MfaApiController, PagesController],
            ),
        ]
    )
    app.add_provider(MfaProvider())
    return app


__all__ = ["create_app"]
