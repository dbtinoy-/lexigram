"""Root module for the feedback-loop demo."""

from __future__ import annotations

import os

from feedback_loop.controllers.api import LoopApiController
from feedback_loop.di.provider import LoopProvider
from feedback_loop.services.loop_service import LoopService
from feedback_loop.ui.pages import LoopPageController
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.module import EvaluationModule
from lexigram.ai.feedback.config import FeedbackConfig
from lexigram.ai.feedback.module import FeedbackModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig


@module()
class FeedbackLoopModule(Module):
    """Ratings-to-regression loop with tracked experiments."""

    @classmethod
    def configure(
        cls,
        port: int | None = None,
        experiment_dir: str = ".runs",
    ) -> DynamicModule:
        selected_port = (
            port
            if port is not None
            else int(os.environ.get("FEEDBACK_LOOP_PORT", "8086"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                FeedbackModule.configure(FeedbackConfig(async_processing=False)),
                EvaluationModule.configure(
                    EvaluationConfig(
                        default_threshold=0.6,
                        default_seed=7,
                        experiment_dir=experiment_dir,
                    )
                ),
                WebModule.configure(
                    controllers=[LoopApiController, LoopPageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[LoopProvider],
            exports=[LoopService],
        )


__all__ = ["FeedbackLoopModule"]
