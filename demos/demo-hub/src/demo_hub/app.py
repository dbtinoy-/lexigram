"""Application composition root for the demo hub."""

from __future__ import annotations

from demo_hub.config import APP_YAML
from demo_hub.controllers.api import HubApiController
from demo_hub.di.provider import HubProvider
from demo_hub.ui.pages import HubPageController
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) hub application."""
    config = config or LexigramConfig.from_yaml(APP_YAML)
    web_config = config.get_section("web", WebConfig)

    app = Application(name="demo-hub", config=config)
    app.add_modules(
        [
            WebModule.configure(
                web_config=web_config,
                controllers=[HubApiController, HubPageController],
            ),
        ]
    )
    app.add_provider(HubProvider())
    return app


__all__ = ["create_app"]
