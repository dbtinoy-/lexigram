"""Composition root for the event-driven orders demo.

Every Lexigram application has exactly one place that knows how the pieces
fit together — the **composition root** — and here it is deliberately tiny:

1. **Capabilities**: framework ``Module.configure(...)`` bundles. Each
   framework package reads its own section of ``application.yaml`` through
   provider auto-injection (``config_key`` / ``config_model``), so you pass
   *nothing* — just list the controllers your app contributes.
2. **Services**: this demo's own ``Provider`` (imperative register/boot
   lifecycle for stateful services — see ``di/provider.py``).

This demo's lesson is CQRS with an event-driven read side: writes enter the
``CommandBus`` (place/pay/ship), command handlers persist through the
repository and append to an outbox, and the ``EventBus`` fans domain events
out to projections and notifications. All of that wiring lives in
``OrdersProvider.boot`` — none of it here.

Run with ``uv run python -m orders serve``.
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.events.module import EventsModule
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from orders.config import load_lex_config
from orders.controllers.api import OrdersApiController
from orders.di.provider import OrdersProvider
from orders.ui.pages import OrdersPageController


def build_modules(config: LexigramConfig) -> list[object]:
    """Declarative capabilities — framework modules bound to typed sections.

    ``config`` stays explicit here because demos live in subdirectories:
    binding against this demo's own ``application.yaml`` (absolute path)
    keeps behavior identical no matter the caller's working directory.
    """
    return [
        # No config argument → framework defaults: in-memory event store plus
        # the CommandBusProtocol/EventBusProtocol bindings the demo resolves.
        EventsModule.configure(),
        WebModule.configure(
            web_config=config.get_section("web", WebConfig),
            controllers=[OrdersApiController, OrdersPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo."""
    return [OrdersProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Programmatic/tests entry point. For serving, prefer the idiomatic
    ``Application.boot(...)`` context manager shown in ``main.serve`` —
    it guarantees ``stop()`` even on exceptions or Ctrl-C.
    """
    config = config or load_lex_config()
    app = Application(name="event-driven-orders", config=config)
    app.add_modules(build_modules(config))
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
