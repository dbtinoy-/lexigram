"""Tracer — tracks request timing and tracing information."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class TraceSpan:
    """A single trace span."""

    name: str
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)


class Tracer:
    """Tracks request timing and tracing information.

    Demonstrates observability patterns with trace spans.
    """

    def __init__(self, metrics: Any) -> None:
        self._metrics = metrics
        self._spans: list[TraceSpan] = []

    def start_span(
        self, name: str, attributes: dict[str, Any] | None = None
    ) -> TraceSpan:
        """Start a new trace span."""
        span = TraceSpan(name=name, attributes=attributes or {})
        self._spans.append(span)
        return span

    def end_span(self, span: TraceSpan) -> None:
        """End a trace span and record metrics."""
        span.end_time = time.time()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        self._metrics.record_histogram("trace_duration_ms", span.duration_ms)

    def get_spans(self) -> list[dict[str, Any]]:
        """Get all trace spans."""
        return [
            {
                "name": s.name,
                "duration_ms": s.duration_ms,
                "attributes": s.attributes,
            }
            for s in self._spans
        ]

    def clear_spans(self) -> int:
        """Clear all trace spans."""
        count = len(self._spans)
        self._spans.clear()
        return count
