"""Public protocol surface for ``lexigram.monitor``."""

from __future__ import annotations

from lexigram.contracts.observability.metrics import (
    AlertDispatcherProtocol,
    MetricProtocol,
    MetricsBackendProtocol,
    MetricsCollectorProtocol,
)
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.contracts.observability.tracing import TracerProtocol as TraceProvider
from lexigram.monitor.types import HealthCheckerProtocol

__all__ = [
    "AlertDispatcherProtocol",
    "HealthCheckerProtocol",
    "MetricProtocol",
    "MetricsBackendProtocol",
    "MetricsCollectorProtocol",
    "TraceProvider",
    "TracerProtocol",
]
