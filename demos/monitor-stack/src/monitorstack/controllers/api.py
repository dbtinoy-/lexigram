"""Monitor API — HTTP surface for monitoring operations.

Controllers are thin: they validate input, call a service, and
return a response dict.  No business logic lives here.
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get, post


class MonitorApiController(Controller):
    """HTTP surface for monitoring operations.

    Delegates to services for business logic.  Returns dicts that
    the framework serialises to JSON.
    """

    prefix = "/api/monitor"

    def __init__(self, health_checker: object = None, tracer: object = None, metrics: object = None) -> None:
        self._health_checker = health_checker
        self._tracer = tracer
        self._metrics = metrics

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Run health checks and return status."""
        return await self._health_checker.check_health()

    @get("/metrics")
    async def metrics(self) -> dict[str, Any]:
        """Get all collected metrics."""
        return self._metrics.get_all_metrics()

    @get("/traces")
    async def traces(self) -> dict[str, Any]:
        """Get all trace spans."""
        spans = self._tracer.get_spans()
        return {"count": len(spans), "spans": spans}

    @post("/trace")
    async def create_trace(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create a trace span with timing."""
        name = body.get("name", "unnamed")
        attributes = body.get("attributes", {})

        span = self._tracer.start_span(name, attributes)
        # Simulate some work
        import asyncio
        await asyncio.sleep(0.01)
        self._tracer.end_span(span)

        return {"span": {"name": span.name, "duration_ms": span.duration_ms}}

    @get("/health/self")
    async def health_self(self) -> dict[str, Any]:
        """Self health check."""
        result = await self._health_checker.check_self()
        return {
            "component": result.component,
            "status": result.status.value,
            "message": result.message,
        }

    @post("/metrics/increment")
    async def increment_metric(self, body: dict[str, Any]) -> dict[str, Any]:
        """Increment a counter metric."""
        name = body.get("name", "")
        if not name:
            return {"error": "Metric name is required"}

        value = body.get("value", 1.0)
        tags = body.get("tags", {})
        self._metrics.increment(name, value, tags)
        return {"status": "ok", "name": name}

    @post("/metrics/gauge")
    async def set_gauge(self, body: dict[str, Any]) -> dict[str, Any]:
        """Set a gauge metric."""
        name = body.get("name", "")
        if not name:
            return {"error": "Metric name is required"}

        value = body.get("value", 0.0)
        tags = body.get("tags", {})
        self._metrics.set_gauge(name, value, tags)
        return {"status": "ok", "name": name}


__all__ = ["MonitorApiController"]
