"""Composition root for the ai-guardrails demo — start reading here.

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
│        LEX_WEB__SERVER__PORT=9000   env vars   ← win over everything    │
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

Run with::

    uv run python -m guard_gate

In a real app, this file is your single source of truth for
what's wired.  Replace the demo modules with your own (e.g. AuthModule,
CacheModule) and swap GuardrailsProvider for your domain provider.
"""

from __future__ import annotations

from guard_gate.controllers.api import GuardApiController
from guard_gate.di.provider import GuardrailsProvider
from guard_gate.ui.pages import PlaygroundPageController
from lexigram.ai.governance import GovernanceModule
from lexigram.ai.guard import GuardModule
from lexigram.app import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.module import WebModule


def build_modules() -> list[object]:
    """Declarative capabilities — zero configuration arguments needed.

    Each ``Module.configure()`` (no args) reads its typed section from
    application.yaml automatically via config_key/config_model on the
    module's providers.  Override per-provider if needed.

    Modules are framework packages (Guard, Governance, Web).
    Each .configure() returns a DynamicModule that the container knows
    how to register and boot.  The order here defines priority — Web
    should come last so domain services resolve first.
    """
    return [
        # Guard: injection detection, PII redaction, length limits.
        # Reads ``ai_guard:`` from application.yaml automatically.
        GuardModule.configure(),
        # Governance: budget tracking, restricted models, audit trail.
        # Reads ``ai_governance:`` from application.yaml automatically.
        GovernanceModule.configure(),
        # Web: Starlette server + middleware.  Controllers are your HTTP
        # surface.  Omit PlaygroundPageController + delete ui/ if using
        # an external frontend.
        WebModule.configure(
            controllers=[GuardApiController, PlaygroundPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo.

    Providers register YOUR services (not framework ones).
    A real app typically has one Provider per domain area (e.g.
    OrdersProvider, UsersProvider).  Each gets a register()/boot() pair.
    """
    return [GuardrailsProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Use this in tests (boot it yourself) or hand to ``main.py`` which
    calls ``app.start()`` / ``app.stop()``.

    Separating creation from startup lets tests control
    lifecycle precisely.  The app object holds the container — all
    service resolution goes through it.

    Args:
        config: Optional pre-loaded config. When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.
    """
    app = Application(name="ai-guardrails", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
