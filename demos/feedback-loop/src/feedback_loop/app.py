"""Composition root for the feedback-loop demo.

Every Lexigram application has exactly one place that knows how the pieces
fit together: the composition root.  Everything else (controllers,
services, views) is inert until this file wires it.

``application.yaml`` lives next to this demo's root; the framework
auto-discovers it from the working directory.  No explicit config loading
is needed — ``FeedbackModule.configure()``, ``EvaluationModule.configure()``,
and ``WebModule.configure()`` read their typed sections from the loaded
config via ``config_key`` / ``config_model``.

Convention: declarative module/provider registration.  This file declares
*what* the app needs; the framework resolves *how* to build it at boot.
"""

from __future__ import annotations

from feedback_loop.controllers import LoopApiController
from feedback_loop.di import LoopProvider
from feedback_loop.ui import LoopPageController
from lexigram.ai.evaluation import EvaluationModule
from lexigram.ai.feedback import FeedbackModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web import WebModule


def build_modules() -> list[object]:
    """Declarative capabilities — zero configuration arguments needed.

    Each ``Module.configure(...)`` returns a DynamicModule: a recipe the
    framework expands into providers at boot.  Because every provider in
    the bundle declares ``config_key`` / ``config_model``, the orchestrator
    injects the matching typed section of ``LexigramConfig`` into
    ``provider.config`` right before ``register()`` runs.
    """
    return [
        # Synchronous capture: no background queue, so "submit → read back"
        # works within one request.  Reads ai_feedback: from yaml.
        FeedbackModule.configure(),
        # Fixed threshold/seed/experiment dir: evaluation runs are
        # reproducible across restarts.  Reads ai_evaluation: from yaml.
        EvaluationModule.configure(),
        # Web: Starlette server + middleware.  Controllers are your HTTP
        # surface.  Reads web: from yaml.
        WebModule.configure(
            controllers=[LoopApiController, LoopPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo."""
    return [LoopProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in CREATED state (not yet started).

    Modules declare capabilities; providers fill services.
    The dependency graph resolves lazily at boot.

    Args:
        config: Optional pre-loaded config. When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.
    """
    app = Application(name="feedback-loop", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
