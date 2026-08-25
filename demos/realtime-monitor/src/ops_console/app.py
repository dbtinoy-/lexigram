"""Application composition root for the realtime-monitor demo.

``create_app`` is the only place that knows how the modules fit together;
sections are bound inline from the demo's ``application.yaml``.
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from ops_console.config import RealtimeConfig, load_lex_config
from ops_console.controllers.api import ConsoleController
from ops_console.controllers.operator import OperatorHandler
from ops_console.di.provider import RealtimeProvider
from ops_console.ui.pages import PagesController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) realtime application."""
    config = config or load_lex_config()
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
