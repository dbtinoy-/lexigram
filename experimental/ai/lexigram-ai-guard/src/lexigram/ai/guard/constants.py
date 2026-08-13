"""GuardProtocol constants — thresholds, error codes, and metric names."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-guard")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefixes -------------------------------------------
ENV_PREFIX: str = "LEX_AI_GUARD__"
"""Environment variable prefix for Guard configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Delimiter for nested env var keys."""


# ---------------------------------------------------------------------------
# Default safety thresholds
# ---------------------------------------------------------------------------

# Default confidence threshold above which an input is flagged as unsafe.
DEFAULT_DETECTION_THRESHOLD: float = 0.85

# Maximum allowed prompt length in characters before truncation.
DEFAULT_MAX_INPUT_LENGTH: int = 32_768

# Default maximum output length in characters.
DEFAULT_MAX_OUTPUT_LENGTH: int = 16_384

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

ERROR_INPUT_GUARD_VIOLATION: str = "LEX_GUARD_001"
ERROR_OUTPUT_GUARD_VIOLATION: str = "LEX_GUARD_002"
ERROR_GUARD_CONFIG_INVALID: str = "LEX_GUARD_003"

# ---------------------------------------------------------------------------
# MetricProtocol names
# ---------------------------------------------------------------------------

METRIC_GUARD_CHECKS_TOTAL: str = "ai.guard.checks.total"
METRIC_GUARD_VIOLATIONS_TOTAL: str = "ai.guard.violations.total"
METRIC_GUARD_CHECK_DURATION_MS: str = "ai.guard.check.duration_ms"

__all__ = [
    "DEFAULT_DETECTION_THRESHOLD",
    "DEFAULT_MAX_INPUT_LENGTH",
    "DEFAULT_MAX_OUTPUT_LENGTH",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "ERROR_GUARD_CONFIG_INVALID",
    "ERROR_INPUT_GUARD_VIOLATION",
    "ERROR_OUTPUT_GUARD_VIOLATION",
    "METRIC_GUARD_CHECKS_TOTAL",
    "METRIC_GUARD_CHECK_DURATION_MS",
    "METRIC_GUARD_VIOLATIONS_TOTAL",
    "__version__",
]
