"""Composition root for the realtime-monitor demo — start reading here.

Every Lexigram application has exactly one place that knows how the pieces
fit together: the **composition root**.  Everything else (controllers,
services, templates) is inert until *this file* wires it.

The mental model has three layers.  Once these click, every Lexigram app
reads the same way:

┌─────────────────────────────────────────────────────────────────────────┐
│ 1. CONFIGURATION                                                        │
│    ``application.yaml`` holds your values.  The framework loads it,     │
│    merges overrides on top (highest → lowest):                          │
│                                                                         │
│        LEX_DEMO__HEARTBEAT_INTERVAL_SECONDS=5  env vars  ← win         │
│        application.production.yaml  profile overlay                     │
│        application.yaml             base file                           │
│        dataclass field defaults     last resort                         │
│                                                                         │
│    Result: ONE typed ``LexigramConfig`` object.                         │
│                                                                         │
│ 2. CAPABILITIES (declarative)                                           │
│    ``Module.configure(...)`` switches framework packages on and tells   │
│    them which controllers are yours.  Each package reads its own yaml   │
│    section through its config model.                                    │
│                                                                         │
│ 3. SERVICES (imperative)                                               │
│    A ``Provider`` registers the services *you* wrote into the DI        │
│    container, with register/boot/shutdown lifecycle hooks.              │
└─────────────────────────────────────────────────────────────────────────┘

Two wiring styles are supported everywhere; both produce identical
runtime behavior:

- **Explicit** (this file): sections passed to ``configure(config=...)``
  make the wiring visible and testable at the composition root.
- **Automatic**: call ``configure()`` with no arguments — providers declare
  ``config_key``/``config_model``, so the orchestrator injects their typed
  section from the loaded config before boot.

Unknown/typo keys (``prot:`` vs ``port:``) fail startup with a
did-you-mean suggestion instead of silently falling back to defaults.

Run with::

    PYTHONPATH=src uv run python -m ops_console
"""

from __future__ import annotations

from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.module import WebModule
from ops_console.controllers.api import ConsoleController
from ops_console.controllers.operator import OperatorHandler
from ops_console.di.provider import RealtimeProvider
from ops_console.ui.pages import PagesController

# Lexigram follows a strict dependency direction: application code imports
# framework packages, never the reverse.  This file is the only place
# that references both framework modules AND your controllers/providers.


def build_modules() -> list[object]:
    """Declarative capabilities — zero configuration arguments needed.

    Each ``Module.configure(...)`` returns a DynamicModule: a recipe the
    framework expands into providers at boot.  Because every provider in
    the bundle declares ``config_key`` / ``config_model``, the orchestrator
    injects the matching typed section of ``LexigramConfig`` into
    ``provider.config`` right before ``register()`` runs — YAML values and
    ``LEX_*`` environment overrides already merged.
    """
    return [
        WebModule.configure(
            controllers=[ConsoleController, OperatorHandler, PagesController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo.

    A Provider is Lexigram's unit of lifecycle management: ``register()``
    binds services into the DI container, ``boot()`` runs post-registration
    setup (here: starting the heartbeat producer), ``shutdown()`` cleans up.
    """
    return [RealtimeProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Use this directly in tests (boot it yourself so you control the
    lifecycle) or hand the pieces to :meth:`Application.start` as
    ``main.serve`` does — the ``finally`` block ensures ``stop()`` runs
    even when something raises.

    Args:
        config: Optional pre-loaded config. When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.
    """
    app = Application(name="realtime-monitor", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
