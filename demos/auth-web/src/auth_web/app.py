"""Application composition root for the auth web demo.

``create_app`` is the only place that knows how the modules fit together;
the auth section is coerced eagerly (nested token dicts can load shallow)
and passed explicitly to :class:`AuthModule`.
"""

from __future__ import annotations

from auth_web.config import load_lex_config
from auth_web.controllers.api import AuthApiController
from auth_web.di.provider import AuthWebProvider
from auth_web.ui.pages import PagesController
from lexigram.app.base import Application
from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.auth.module import AuthModule
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def _coerce_auth_config(auth_config: AuthConfig) -> AuthConfig:
    """Normalize nested sections that can load as raw dicts."""
    token = getattr(auth_config, "token", None)
    if isinstance(token, dict):
        return auth_config.model_copy(update={"token": JWTConfig(**token)}, deep=True)
    return auth_config


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) application."""
    config = config or load_lex_config()
    auth_config = _coerce_auth_config(config.get_section("auth", AuthConfig))
    web_config = config.get_section("web", WebConfig)

    app = Application(name="auth-web", config=config)
    app.add_modules(
        [
            AuthModule.configure(config=auth_config),
            WebModule.configure(
                web_config=web_config,
                controllers=[AuthApiController, PagesController],
            ),
        ]
    )
    app.add_provider(AuthWebProvider())
    return app


__all__ = ["create_app"]
