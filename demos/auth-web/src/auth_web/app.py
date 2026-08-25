"""Application composition root for the auth-web demo.

``create_app`` is the only place that knows how the modules fit together;
sections are bound inline from the demo's ``application.yaml``.
"""

from __future__ import annotations

from auth_web.config import load_lex_config
from auth_web.controllers.api import AuthApiController
from auth_web.di.provider import AuthWebProvider
from auth_web.pages import PagesController
from lexigram.app.base import Application
from lexigram.auth.config import AuthConfig
from lexigram.auth.module import AuthModule
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="auth-web", config=config)
    app.add_modules(
        [
            AuthModule.configure(config=config.get_section("auth", AuthConfig)),
            WebModule.configure(
                web_config=web_config,
                controllers=[AuthApiController, PagesController],
            ),
        ]
    )
    app.add_provider(AuthWebProvider())
    return app


__all__ = ["create_app"]
