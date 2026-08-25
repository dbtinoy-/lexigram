"""Application composition root for the event-driven-orders demo.

``create_app`` is the only place that knows how the modules fit together;
sections are bound inline from the demo's ``application.yaml``.
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.events.module import EventsModule
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from orders.config import load_lex_config
from orders.controllers.api import OrdersApiController
from orders.di.provider import OrdersProvider
from orders.pages import OrdersPageController


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="event-driven-orders", config=config)
    app.add_modules(
        [
            EventsModule.configure(),
            WebModule.configure(
                web_config=web_config,
                controllers=[OrdersApiController, OrdersPageController],
            ),
        ]
    )
    app.add_provider(OrdersProvider())
    return app


__all__ = ["create_app"]
