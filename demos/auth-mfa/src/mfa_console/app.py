"""Composition root for the auth-mfa demo — start reading here.

Every Lexigram application has exactly one place that knows how the pieces
fit together: the **composition root**.  Everything else (controllers,
services, templates) is inert until *this file* wires it.

Three layers:

1. CONFIGURATION — ``application.yaml`` holds your values.  The framework
   loads it; ``LEX_*`` env vars win over yaml.

2. CAPABILITIES (declarative) — ``Module.configure(...)`` switches
   framework packages on.  Each reads its own yaml section automatically.

3. SERVICES (imperative) — a ``Provider`` registers the services *you*
   wrote into the DI container.

Run with::

    cd demos/auth-mfa
    PYTHONPATH=src uv run python -m mfa_console
"""

from __future__ import annotations

from lexigram.app.base import Application  # Application = the bootable object
from lexigram.auth.module import AuthModule  # framework module — owns auth providers
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider  # base class for your DI registrations
from lexigram.web.module import WebModule  # framework module — owns web server
from mfa_console.controllers.api import MfaApiController  # your HTTP surface
from mfa_console.di.provider import MfaProvider  # your service registrations
from mfa_console.ui.pages import PagesController  # page controller (optional)


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
        AuthModule.configure(),  # sessions, tokens, RBAC roles
        # WebModule is the only module that needs your controllers list —
        # this is the explicit wiring style.  Omit PagesController if you
        # use an external frontend (React, Vue, etc.).
        WebModule.configure(
            controllers=[MfaApiController, PagesController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo.

    A Provider is Lexigram's unit of lifecycle management: ``register()``
    binds services into the DI container, ``boot()`` runs post-registration
    setup (here: seeding personas, enrolling TOTP), ``shutdown()`` cleans up.
    """
    return [MfaProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Use this directly in tests (boot it yourself so you control the
    lifecycle) or hand the pieces to :meth:`Application.start` as
    ``main.py`` does — the context manager guarantees ``stop()`` even
    when something raises.

    Args:
        config: Optional pre-loaded config. When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.
    """
    app = Application(name="mfa-console", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
