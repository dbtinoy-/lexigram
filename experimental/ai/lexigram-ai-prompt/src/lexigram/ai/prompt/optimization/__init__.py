"""Prompt optimization subsystem — public exports."""

from __future__ import annotations

from lexigram.ai.prompt.optimization.few_shot import DynamicFewShotSelector
from lexigram.ai.prompt.optimization.optimizer import PromptOptimizer
from lexigram.ai.prompt.optimization.types import (
    EvaluationMetric,
    Example,
    OptimizationError,
    OptimizationStrategy,
    OptimizedPrompt,
)

__all__ = [
    "DynamicFewShotSelector",
    "EvaluationMetric",
    "Example",
    "OptimizationError",
    "OptimizationStrategy",
    "OptimizedPrompt",
    "PromptOptimizer",
]
