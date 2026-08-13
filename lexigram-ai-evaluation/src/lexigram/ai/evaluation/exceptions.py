"""Exceptions for the AI Evaluation subsystem."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import EvaluationError as BaseEvaluationError


class EvaluationConfigError(BaseEvaluationError):
    """Raised when evaluation configuration is invalid."""


class EvaluatorNotFoundError(BaseEvaluationError):
    """Raised when a requested evaluator cannot be found."""


class DatasetError(BaseEvaluationError):
    """Raised when there's an error with the evaluation dataset."""


class HarnessError(BaseEvaluationError):
    """Raised when the evaluation harness encounters an error."""


class TrackingError(BaseEvaluationError):
    """Raised when experiment tracking cannot persist or read run state."""


class CheckpointError(BaseEvaluationError):
    """Raised when a checkpoint is missing or fails digest verification."""


class AblationError(BaseEvaluationError):
    """Raised when an ablation references unknown checkpoints."""


class AnalysisError(BaseEvaluationError):
    """Raised when a run analysis cannot be produced."""


__all__ = [
    "AblationError",
    "AnalysisError",
    "CheckpointError",
    "DatasetError",
    "EvaluationConfigError",
    "EvaluatorNotFoundError",
    "HarnessError",
    "TrackingError",
]
