"""Composition root for the feedback-loop demo.

Every Lexigram application has exactly one place that knows how the pieces
fit together — the **composition root** — and here it is deliberately tiny:

1. **Capabilities**: framework ``Module.configure(...)`` bundles. Each
   framework package reads its own section of ``application.yaml`` through
   provider auto-injection (``config_key`` / ``config_model``), so you pass
   *nothing* — just list the controllers your app contributes.
2. **Services**: this demo's own ``Provider`` (imperative register/boot
   lifecycle for stateful services — see ``di/provider.py``).

This demo's lesson is closing the loop: ``FeedbackModule`` captures
structured ratings into its store (synchronously here, so a submitted rating
is queryable in the same request), and ``EvaluationModule`` scores responses
against thresholds with reproducible seeds. ``LoopProvider`` composes both so
the API can capture feedback and immediately evaluate against it.

Run with ``uv run python -m feedback_loop serve``.
"""

from __future__ import annotations

from feedback_loop.config import load_lex_config
from feedback_loop.controllers.api import LoopApiController
from feedback_loop.di.provider import LoopProvider
from feedback_loop.ui.pages import LoopPageController
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.module import EvaluationModule
from lexigram.ai.feedback.config import FeedbackConfig
from lexigram.ai.feedback.module import FeedbackModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def build_modules(config: LexigramConfig) -> list[object]:
    """Declarative capabilities — framework modules bound to typed sections.

    ``config`` stays explicit here because demos live in subdirectories:
    binding against this demo's own ``application.yaml`` (absolute path)
    keeps behavior identical no matter the caller's working directory.
    """
    return [
        # Synchronous capture: no background queue, so "submit → read back"
        # works within one request — ideal for teaching the loop.
        FeedbackModule.configure(FeedbackConfig(async_processing=False)),
        # Fixed threshold/seed/experiment dir: evaluation runs are
        # reproducible across restarts of the demo.
        EvaluationModule.configure(
            EvaluationConfig(
                default_threshold=0.6,
                default_seed=7,
                experiment_dir=".runs",
            )
        ),
        WebModule.configure(
            web_config=config.get_section("web", WebConfig),
            controllers=[LoopApiController, LoopPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    """Imperative services owned by this demo."""
    return [LoopProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the application in ``CREATED`` state (not yet started).

    Programmatic/tests entry point. For serving, prefer the idiomatic
    ``Application.boot(...)`` context manager shown in ``main.serve`` —
    it guarantees ``stop()`` even on exceptions or Ctrl-C.
    """
    config = config or load_lex_config()
    app = Application(name="feedback-loop", config=config)
    app.add_modules(build_modules(config))
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]
