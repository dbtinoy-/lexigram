"""Application composition root for the realtime-monitor demo."""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from ops_console.config import APP_YAML, RealtimeConfig
from ops_console.controllers.api import ConsoleController
from ops_console.controllers.operator import OperatorHandler
from ops_console.di.provider import RealtimeProvider
from ops_console.ui.pages import PagesController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) realtime application."""
    config = config or LexigramConfig.from_yaml(APP_YAML)
    web_config = config.get_section("web", WebConfig)
    demo_config = config.get_section("demo", RealtimeConfig)

    app = Application(name="realtime-monitor", config=config)
    app.add_modules(
        [
            WebModule.configure(
                web_config=web_config,
                controllers=[ConsoleController, OperatorHandler, PagesController],
            ),
        ]
    )
    app.add_provider(RealtimeProvider(config=demo_config))
    return app


__all__ = ["create_app"]
