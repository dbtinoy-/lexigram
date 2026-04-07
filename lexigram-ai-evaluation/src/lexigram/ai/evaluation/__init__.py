"""AI Evaluation framework for Lexigram."""

from __future__ import annotations

from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_THRESHOLD,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES,
)
from lexigram.ai.evaluation.di.provider import EvaluationProvider
from lexigram.ai.evaluation.exceptions import (
    DatasetError,
    EvaluationConfigError,
    EvaluatorNotFoundError,
    HarnessError,
)
from lexigram.ai.evaluation.module import EvaluationModule
from lexigram.ai.evaluation.types import (
    BatchEvaluationResult,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRunContext,
    EvaluationSample,
    RunReport,
)

__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_THRESHOLD",
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_RETRIES",
    "BatchEvaluationResult",
    "DatasetError",
    "EvaluationConfig",
    "EvaluationConfigError",
    "EvaluationDataset",
    "EvaluationModule",
    "EvaluationProvider",
    "EvaluationResult",
    "EvaluationRunContext",
    "EvaluationSample",
    "EvaluatorNotFoundError",
    "HarnessError",
    "RunReport",
]
