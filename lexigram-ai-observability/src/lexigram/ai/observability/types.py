"""Type definitions for AI Observability."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from lexigram.contracts import (
    HealthCheckResult,
)

# Async health check function signature.
HealthCheckFunc = Callable[[], Coroutine[Any, Any, HealthCheckResult]]

# Metric label map.
MetricLabels = dict[str, str]


__all__ = [
    "HealthCheckFunc",
    "MetricLabels",
]
