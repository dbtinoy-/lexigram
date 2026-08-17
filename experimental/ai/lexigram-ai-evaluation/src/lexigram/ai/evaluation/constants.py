"""Evaluation constants — error codes, metric names, and span names.

Centralised string constants used across the evaluation package to prevent
magic-string drift between modules.
"""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-evaluation")
except ImportError:
    __version__ = "0.0.0"

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD: float = 0.8
DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
MAX_RETRIES: int = 3
DEFAULT_TIMEOUT_SECONDS: int = 30

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_AI_EVALUATION__"
ENV_NESTED_DELIMITER: str = "__"

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

ERROR_DATASET_ERROR: str = "DATASET_ERROR"
ERROR_EVALUATION_CONFIG: str = "EVALUATION_CONFIG_ERROR"
ERROR_EVALUATION_FAILED: str = "EVALUATION_FAILED"
ERROR_EVALUATOR_NOT_FOUND: str = "EVALUATOR_NOT_FOUND"
ERROR_HARNESS_ERROR: str = "HARNESS_ERROR"
ERROR_TIMEOUT: str = "EVALUATION_TIMEOUT"

# ---------------------------------------------------------------------------
# Metric names
# ---------------------------------------------------------------------------

METRIC_DATASET_SAMPLES: str = "evaluation.dataset.samples"
METRIC_EVALUATION_DURATION_MS: str = "evaluation.duration_ms"
METRIC_EVALUATION_PASSED: str = "evaluation.passed"
METRIC_EVALUATION_SCORE: str = "evaluation.score"
METRIC_EVALUATIONS_ERRORS: str = "evaluation.errors"
METRIC_EVALUATIONS_TOTAL: str = "evaluation.total"

# ---------------------------------------------------------------------------
# Span names
# ---------------------------------------------------------------------------

SPAN_DATASET_LOAD: str = "evaluation.dataset.load"
SPAN_EVALUATE: str = "evaluation.evaluate"
SPAN_HARNESS_RUN: str = "evaluation.harness.run"

__all__ = [
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_THRESHOLD",
    "DEFAULT_TIMEOUT_SECONDS",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "ERROR_DATASET_ERROR",
    "ERROR_EVALUATION_CONFIG",
    "ERROR_EVALUATION_FAILED",
    "ERROR_EVALUATOR_NOT_FOUND",
    "ERROR_HARNESS_ERROR",
    "ERROR_TIMEOUT",
    "MAX_RETRIES",
    "METRIC_DATASET_SAMPLES",
    "METRIC_EVALUATIONS_ERRORS",
    "METRIC_EVALUATIONS_TOTAL",
    "METRIC_EVALUATION_DURATION_MS",
    "METRIC_EVALUATION_PASSED",
    "METRIC_EVALUATION_SCORE",
    "SPAN_DATASET_LOAD",
    "SPAN_EVALUATE",
    "SPAN_HARNESS_RUN",
    "__version__",
]
