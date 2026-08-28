"""HTTP surface for Lexigram metrics, health checks, and traces."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.contracts.observability.metrics import MetricsCollectorProtocol
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.monitor.health import HealthCheckRegistry
from lexigram.web import Controller, get, post


class MonitorApiController(Controller):
    """Expose the monitor package's protocols without reimplementing them."""

    prefix = "/api/monitor"

    def __init__(
        self,
        health_registry: HealthCheckRegistry | None = None,
        tracer: TracerProtocol | None = None,
        metrics: MetricsCollectorProtocol | None = None,
        service_name: str = "monitor-console",
    ) -> None:
        self._health_registry = health_registry
        self._tracer = tracer
        self._metrics = metrics
        self._service_name = service_name

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Run Lexigram's categorised health registry."""
        status, details = await self._health_registry.run_all()
        readiness = details.get("readiness", {})
        return {
            "status": status.value,
            "service": self._service_name,
            "timestamp": readiness.get("timestamp"),
            "checks": readiness.get("checks", []),
            "probes": details,
        }

    @get("/metrics")
    async def metrics(self) -> dict[str, Any]:
        """Serialize Lexigram metric instruments for the browser."""
        counters: dict[str, Any] = {}
        gauges: dict[str, Any] = {}
        histograms: dict[str, Any] = {}
        for name, metric in self._metrics.get_all_metrics().items():
            if hasattr(metric, "get_count"):
                counters[name] = metric.get_count()
            elif hasattr(metric, "get_value"):
                gauges[name] = metric.get_value()
            elif hasattr(metric, "get_observations"):
                observations = metric.get_observations()
                histograms[name] = {
                    "count": len(observations),
                    "min": min(observations) if observations else 0,
                    "max": max(observations) if observations else 0,
                    "avg": sum(observations) / len(observations)
                    if observations
                    else 0,
                }
        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
        }

    @get("/traces")
    async def traces(self) -> dict[str, Any]:
        """Return the bounded in-memory spans kept by Lexigram Monitor."""
        spans = [self._span_payload(span) for span in self._tracer.get_all_spans()]
        return {"count": len(spans), "spans": spans}

    @post("/trace")
    async def create_trace(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create and finish a real Lexigram span, recording its duration."""
        name = body.get("name", "unnamed")
        attributes = body.get("attributes", {})
        span = self._tracer.start_span(name, attributes)
        await asyncio.sleep(0.01)
        span.end()
        duration_ms = (span.get_duration() or 0) * 1000
        self._metrics.histogram("demo_trace_duration_ms", duration_ms)
        return {
            "span": {
                "name": span.name,
                "duration_ms": duration_ms,
                "trace_id": span.context.trace_id,
            }
        }

    @get("/health/self")
    async def health_self(self) -> dict[str, Any]:
        """Run the named self-check through the package registry."""
        return await self._health_registry.run_check("self")

    @post("/metrics/increment")
    async def increment_metric(self, body: dict[str, Any]) -> dict[str, Any]:
        """Increment a Lexigram counter instrument."""
        name = body.get("name", "")
        if not name:
            return {"error": "Metric name is required"}
        self._metrics.increment(name, body.get("value", 1.0), body.get("tags", {}))
        return {"status": "ok", "name": name}

    @post("/metrics/gauge")
    async def set_gauge(self, body: dict[str, Any]) -> dict[str, Any]:
        """Set a Lexigram gauge instrument."""
        name = body.get("name", "")
        if not name:
            return {"error": "Metric name is required"}
        self._metrics.gauge(name, body.get("value", 0.0), body.get("tags", {}))
        return {"status": "ok", "name": name}

    @staticmethod
    def _span_payload(span: Any) -> dict[str, Any]:
        """Convert a Lexigram span into JSON-safe fields."""
        return {
            "name": span.name,
            "duration_ms": (span.get_duration() or 0) * 1000,
            "status": span.status.value,
            "attributes": span.attributes,
            "trace_id": span.context.trace_id,
            "span_id": span.context.span_id,
        }


__all__ = ["MonitorApiController"]
