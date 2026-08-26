"""Composition root for the auth-rbac console.

Every Lexigram application has exactly one place that knows how the pieces
fit together — the **composition root** — and here it is deliberately tiny:

1. **Configuration**: one typed ``LexigramConfig`` loaded by the framework
   itself (``LexigramConfig.from_yaml()`` discovers ``application.yaml`` in
   the project root), sliced into typed sections per concern.
2. **Capabilities**: framework ``Module.configure(...)`` bundles receive
   the typed sections they own. Explicit is deliberate: sections passed at
   configure-time drive the whole module wiring (controllers, middleware
   stack), while provider auto-injection separately fills ``provider.config``
   post-registration.
3. **Services**: this demo's own ``Provider`` (imperative register/boot
   lifecycle for stateful services — see ``di/provider.py``).

Run with ``uv run python -m rbac_console`` (from this demo's root, so the
framework can discover ``application.yaml``).
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.auth.module import AuthModule
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule
from rbac_console.controllers.api import RbacApiController
from rbac_console.di.provider import RbacProvider
from rbac_console.ui.pages import PagesController


def build_modules(config: LexigramConfig) -> list[object]:
    """Declarative capabilities bound to their typed yaml sections."""
    return [
        AuthModule.configure(),  # automatic: yaml injected via config_key
        WebModule.configure(
            web_config=config.get_section("web", WebConfig),
            controllers=[RbacApiController, PagesController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo."""
    return [RbacProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Programmatic/tests entry point. For serving, prefer the idiomatic
    ``Application.boot(...)`` context manager shown in ``main.serve`` —
    it guarantees ``stop()`` even on exceptions or Ctrl-C.
    """
    config = config or LexigramConfig.from_yaml()
    app = Application(name="rbac-console", config=config)
    app.add_modules(build_modules(config))
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
