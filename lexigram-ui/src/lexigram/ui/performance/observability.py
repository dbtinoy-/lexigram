"""
Observability utilities for Lexigram UI.

Provides general-purpose in-memory metrics collection for HTMX components.
HTMX-specific tracking, debug panels, and request logging are admin-specific
and live in lexigram.admin.ui.observability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any

# === Metrics Collection ===


class MetricType(str, Enum):
    """Types of metrics to collect."""

    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricProtocol:
    """A single metric data point."""

    name: str
    value: float
    type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time)


class MetricsCollector:
    """
    Collect and track UI metrics.

    This is a simple in-memory collector. For production,
    integrate with Prometheus, StatsD, or similar.
    """

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}

    def _make_key(self, name: str, labels: dict[str, str] | None = None) -> str:
        """Create metric key with labels."""
        if not labels:
            return name
        sorted_labels = sorted(labels.items())
        label_str = ",".join(f"{k}={v}" for k, v in sorted_labels)
        return f"{name}{{{label_str}}}"

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def set(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    def get_histogram_stats(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0)

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()

    def to_dict(self) -> dict[str, Any]:
        """Export all metrics as dictionary."""
        return {
            "counters": dict(self._counters),
            "histograms": {
                k: self.get_histogram_stats(k.split("{")[0]) for k in self._histograms
            },
            "gauges": dict(self._gauges),
        }


__all__ = ["MetricProtocol", "MetricType", "MetricsCollector"]
