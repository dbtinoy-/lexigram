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


__all__ = [
    "DatasetError",
    "EvaluationConfigError",
    "EvaluatorNotFoundError",
    "HarnessError",
]
