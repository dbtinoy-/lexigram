"""Application composition root for the feedback-loop demo."""

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
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) feedback-loop application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="feedback-loop", config=config)
    app.add_modules(
        [
            FeedbackModule.configure(FeedbackConfig(async_processing=False)),
            EvaluationModule.configure(
                EvaluationConfig(
                    default_threshold=0.6,
                    default_seed=7,
                    experiment_dir=".runs",
                )
            ),
            WebModule.configure(
                web_config=web_config,
                controllers=[LoopApiController, LoopPageController],
            ),
        ]
    )
    app.add_provider(LoopProvider())
    return app


__all__ = ["create_app"]
