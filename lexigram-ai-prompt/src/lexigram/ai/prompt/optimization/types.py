"""Prompt optimization — shared types for the optimization subsystem."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from lexigram.ai.prompt.exceptions import OptimizationError
from lexigram.result import Result


class OptimizationStrategy(StrEnum):
    """Strategy used by :class:`PromptOptimizer` to find better prompts."""

    BOOTSTRAP_FEW_SHOT = "bootstrap_few_shot"
    TEMPLATE_REFINEMENT = "template_refinement"
    ENSEMBLE = "ensemble"


@dataclass
class Example:
    """A labelled example used for few-shot selection or optimization.

    Attributes:
        input: The input text or structured data.
        expected_output: The reference / gold-label output.
        metadata: Optional extra metadata (tags, difficulty, domain, etc.).
    """

    input: str
    expected_output: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizedPrompt:
    """Result of a prompt optimization run.

    Attributes:
        template: The best-performing prompt template text.
        few_shot_examples: Selected examples to prepend.
        score: Evaluation score on the held-out validation set (0–1).
        iterations: Number of optimization iterations run.
        strategy: Which strategy produced this result.
    """

    template: str
    few_shot_examples: list[Example]
    score: float
    iterations: int
    strategy: OptimizationStrategy


# Type alias for evaluation metric callbacks.
# Signature: ``async def metric(prediction: str, expected: str) -> float``
EvaluationMetric = Callable[[str, str], float]


__all__ = [
    "EvaluationMetric",
    "Example",
    "OptimizationError",
    "OptimizationStrategy",
    "OptimizedPrompt",
    "Result",
]
