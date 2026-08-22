"""Root module for the feedback-loop demo."""

from __future__ import annotations

from feedback_loop.di.provider import LoopProvider
from feedback_loop.services.loop_service import LoopService
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.module import EvaluationModule
from lexigram.ai.feedback.config import FeedbackConfig
from lexigram.ai.feedback.module import FeedbackModule
from lexigram.di.module import DynamicModule, Module, module


@module()
class FeedbackLoopModule(Module):
    """Ratings-to-regression loop with tracked experiments."""

    @classmethod
    def configure(cls, experiment_dir: str = ".runs") -> DynamicModule:
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
            ],
            providers=[LoopProvider],
            exports=[LoopService],
        )


__all__ = ["FeedbackLoopModule"]
