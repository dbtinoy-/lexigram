"""Evaluation types — concrete implementations for evaluation.

Defines evaluation-specific data structures. Contracts types are re-exported
from contracts as they're used in protocol signatures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.contracts.ai.evaluation import (
    EvaluationDataset,
    EvaluationResult,
    EvaluationSample,
    RunReport,
)


@dataclass
class EvaluationRunContext:
    """Context for a single evaluation run.

    Holds the dataset, evaluator, and configuration for an evaluation run.
    """

    dataset: EvaluationDataset
    """The dataset being evaluated."""

    evaluator_name: str
    """Name of the evaluator."""

    config: dict[str, Any] = field(default_factory=dict)
    """Configuration options for the run."""


@dataclass
class BatchEvaluationResult:
    """Result of running evaluation on multiple samples.

    Contains aggregated results and per-sample details.
    """

    total_samples: int
    """Total number of samples evaluated."""

    passed_samples: int
    """Number of samples that passed the threshold."""

    average_score: float
    """Average score across all samples."""

    results: list[EvaluationResult]
    """Individual sample results."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the run."""


__all__ = [
    "BatchEvaluationResult",
    "EvaluationDataset",
    "EvaluationResult",
    "EvaluationRunContext",
    "EvaluationSample",
    "RunReport",
]
