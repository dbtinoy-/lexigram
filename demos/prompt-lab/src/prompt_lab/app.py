"""Composition root for the prompt-lab demo — start reading here.

Every Lexigram application has exactly one place that knows how the pieces
fit together: the **composition root**.  Everything else (controllers,
services, views) is inert until *this file* wires it.

The mental model has three layers.  Once these click, every Lexigram app
reads the same way:

┌─────────────────────────────────────────────────────────────────────────┐
│ 1. CONFIGURATION                                                        │
│    ``application.yaml`` holds your values.  The framework loads it,     │
│    merges overrides on top (highest → lowest):                          │
│                                                                         │
│        LEX_WEB__SERVER__PORT=9000   env vars   ← win over everything    │
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

    uv run python -m prompt_lab
"""

from __future__ import annotations

from lexigram.ai.prompt.module import (
    PromptModule,  # framework module — owns prompt rendering
)
from lexigram.app.base import Application  # Application = the bootable object
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider  # base class for your DI registrations
from lexigram.web.module import WebModule  # framework module — owns web server
from prompt_lab.controllers.api import LabApiController  # your HTTP surface
from prompt_lab.di.provider import LabProvider  # your service registrations
from prompt_lab.ui.pages import LabPageController  # page controller (optional)

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
        # Each Module.configure() returns a DynamicModule recipe.
        # The orchestrator expands recipes into providers, injects their
        # typed config sections from LexigramConfig, then calls register().
        PromptModule.configure(),  # template rendering, sanitisation, validation
        # WebModule is the only module that needs your controllers list —
        # this is the explicit wiring style.  Omit LabPageController if you
        # use an external frontend (React, Vue, etc.).
        WebModule.configure(
            controllers=[LabApiController, LabPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo.

    A Provider is Lexigram's unit of lifecycle management: ``register()``
    binds services into the DI container, ``boot()`` runs post-registration
    setup (here: seeding prompt revisions), ``shutdown()`` cleans up.
    """
    return [LabProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in CREATED state (not yet started).

    Use this directly in tests (boot it yourself so you control the
    lifecycle) or hand the pieces to ``main.serve`` which calls
    ``app.start()`` / ``app.stop()`` — the finally block guarantees
    ``stop()`` even when something raises.

    Args:
        config: Optional pre-loaded config. When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.
    """
    # Application is created in CREATED state — not yet started.
    # Modules declare capabilities; providers fill services.
    # The dependency graph resolves lazily at boot.
    app = Application(name="prompt-lab", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
