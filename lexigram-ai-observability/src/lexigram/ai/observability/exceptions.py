"""Exception hierarchy for AI Observability."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError


class ObservabilityError(AIError):
    """Base exception for all observability-related errors."""

    _code: str = "LEX_ERR_OBS_001"


class HealthCheckError(ObservabilityError):
    """Raised when a health check infrastructure operation fails."""

    _code: str = "LEX_ERR_OBS_002"


class MetricsError(ObservabilityError):
    """Raised when a metrics recording or retrieval operation fails."""

    _code: str = "LEX_ERR_OBS_003"


class TracingError(ObservabilityError):
    """Raised when a tracing operation fails."""

    _code: str = "LEX_ERR_OBS_004"


__all__ = [
    "HealthCheckError",
    "MetricsError",
    "ObservabilityError",
    "TracingError",
]
