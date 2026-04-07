"""
Observability utilities for Lexigram Admin UI.

Provides metrics collection, logging helpers, and debug tools
for monitoring HTMX-powered components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from time import time
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.serialization import dumps_str
from lexigram.ui import Zones, el, render_to_string

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


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


class MetricsCollectorProtocol:
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


# === HTMX-Specific Metrics ===


def track_htmx_request(
    resource: str,
    target: str,
    action: str,
    context: Any | None = None,
) -> None:
    """Track an HTMX request."""
    from lexigram.admin.lib.di import get_admin_resolver

    resolver = get_admin_resolver(context)
    metrics = resolver.resolve_sync(MetricsCollectorProtocol)  # type: ignore[attr-defined]
    metrics.inc(
        "htmx_requests_total",
        labels={"resource": resource, "target": target, "action": action},
    )


def track_render_time(
    resource: str,
    zone: str,
    duration_ms: float,
    context: Any | None = None,
) -> None:
    """Track component render time."""
    from lexigram.admin.lib.di import get_admin_resolver

    resolver = get_admin_resolver(context)
    metrics = resolver.resolve_sync(MetricsCollectorProtocol)  # type: ignore[attr-defined]
    metrics.observe(
        "htmx_render_seconds",
        duration_ms / 1000,
        labels={"resource": resource, "zone": zone},
    )


def track_error(
    resource: str,
    error_type: str,
    status_code: int,
    context: Any | None = None,
) -> None:
    """Track an error."""
    from lexigram.admin.lib.di import get_admin_resolver

    resolver = get_admin_resolver(context)
    metrics = resolver.resolve_sync(MetricsCollectorProtocol)  # type: ignore[attr-defined]
    metrics.inc(
        "htmx_errors_total",
        labels={
            "resource": resource,
            "error_type": error_type,
            "status_code": str(status_code),
        },
    )


# === Logging Helpers ===


def log_htmx_request(
    request: Any,
    resource: str,
    state: Any = None,
) -> None:
    """Log an HTMX request with structured data."""
    is_htmx = getattr(request, "headers", {}).get("HX-Request") == "true"
    target = getattr(request, "headers", {}).get("HX-Target", "")
    trigger = getattr(request, "headers", {}).get("HX-Trigger", "")

    logger.info(
        "htmx_request",
        resource=resource,
        is_htmx=is_htmx,
        target=target,
        trigger=trigger,
        method=getattr(request, "method", ""),
        path=str(getattr(request, "url", "")),
        state=state.to_query_params()
        if state and hasattr(state, "to_query_params")
        else None,
    )


def log_htmx_response(
    resource: str,
    zone: str,
    render_time_ms: float,
    status_code: int = 200,
) -> None:
    """Log an HTMX response with timing."""
    logger.info(
        "htmx_response",
        resource=resource,
        zone=zone,
        render_time_ms=render_time_ms,
        status_code=status_code,
    )


# === Debug Panel ===


def render_debug_panel(
    state: Any = None,
    zones_info: dict[str, bool] | None = None,
    render_time_ms: float | None = None,
) -> str:
    """
    Render a debug panel showing current state and zones.

    Only shown in development mode.

    Args:
        state: Current TableState
        zones_info: Dict of zone_id -> is_rendered
        render_time_ms: Render time for this request

    Returns:
        HTML string for debug panel
    """
    from lexigram.logging.debug import is_debug_mode

    # Only show in debug mode
    if not is_debug_mode():
        return ""

    state_json = "{}"
    if state and hasattr(state, "to_query_params"):
        state_json = dumps_str(state.to_query_params(), indent=2)

    zone_els: list[Any] = []
    for zone in Zones.all_zones():
        rendered = zones_info.get(zone.id, False) if zones_info else False
        status_class = "text-green-500" if rendered else "text-gray-400"
        status_icon = "●" if rendered else "○"
        zone_els.append(el("div", f"{status_icon} {zone.id}", class_=status_class))

    timing_el: Any = ""
    if render_time_ms is not None:
        color = (
            "text-green-500"
            if render_time_ms < 50
            else "text-yellow-500"
            if render_time_ms < 100
            else "text-red-500"
        )
        timing_el = el("div", f"{render_time_ms:.2f}ms", class_=f"{color} font-mono")

    return str(
        render_to_string(
            el(
                "div",
                el(
                    "details",
                    el("summary", "🐛 Debug", class_="cursor-pointer font-medium"),
                    el(
                        "div",
                        el("h4", "State", class_="font-medium mt-2"),
                        el(
                            "pre",
                            state_json,
                            class_="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-auto max-h-40",
                        ),
                        el("h4", "Zones", class_="font-medium mt-2"),
                        el(
                            "div",
                            *zone_els,
                            class_="text-xs font-mono grid grid-cols-2 gap-1",
                        ),
                        timing_el,
                        class_="mt-2",
                    ),
                    class_="p-2",
                ),
                class_="fixed bottom-4 right-4 z-50 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg text-sm max-w-xs",
                id="debug-panel",
            ),
        ),
    )


# === Middleware Decorator ===


def observe_htmx(resource: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to observe HTMX endpoint with metrics and logging.

    Usage:
        @observe_htmx("users")
        async def list_users(request):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
            start = time()

            # Log request
            log_htmx_request(request, resource)

            # Track request
            target = getattr(request, "headers", {}).get("HX-Target", "unknown")
            track_htmx_request(resource, target, "list", context=request)

            try:
                result = await func(request, *args, **kwargs)

                # Log and track response
                elapsed_ms = (time() - start) * 1000
                log_htmx_response(resource, target, elapsed_ms)
                track_render_time(resource, target, elapsed_ms, context=request)

                return result
            except Exception as e:  # noqa: BLE001 — observability wrapper must capture any exception for error tracking before re-raising
                # Track error
                track_error(resource, type(e).__name__, 500, context=request)
                raise

        @wraps(func)
        def sync_wrapper(request: Any, *args: Any, **kwargs: Any) -> Any:
            start = time()

            log_htmx_request(request, resource)
            target = getattr(request, "headers", {}).get("HX-Target", "unknown")
            track_htmx_request(resource, target, "list", context=request)

            try:
                result = func(request, *args, **kwargs)
                elapsed_ms = (time() - start) * 1000
                log_htmx_response(resource, target, elapsed_ms)
                track_render_time(resource, target, elapsed_ms, context=request)
                return result
            except Exception as e:  # noqa: BLE001 — observability wrapper must capture any exception for error tracking before re-raising
                track_error(resource, type(e).__name__, 500, context=request)
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# === Health Check ===


def get_health_status(context: Any | None = None) -> dict[str, Any]:
    """
    Get health status for the UI system.

    Returns:
        Dictionary with health check data
    """
    from lexigram.admin.lib.di import get_admin_resolver

    resolver = get_admin_resolver(context)
    metrics = resolver.resolve_sync(MetricsCollectorProtocol)  # type: ignore[attr-defined]
    stats = metrics.to_dict()

    # Calculate error rate
    total_requests = sum(
        v for k, v in stats["counters"].items() if k.startswith("htmx_requests_total")
    )
    total_errors = sum(
        v for k, v in stats["counters"].items() if k.startswith("htmx_errors_total")
    )
    error_rate = total_errors / total_requests if total_requests > 0 else 0

    return {
        "status": "healthy" if error_rate < 0.05 else "degraded",
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": error_rate,
        "metrics": stats,
    }
