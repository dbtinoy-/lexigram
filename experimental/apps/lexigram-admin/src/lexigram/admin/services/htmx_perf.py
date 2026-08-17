"""HTMX performance monitoring for Lexigram Admin.

For pure HTMX attribute helpers (hx_swap_oob, hx_prefetch, etc.)
see lexigram.ui.htmx.helpers.
"""

from __future__ import annotations

from typing import Any


class HTMXPerformanceMonitor:
    """Monitor and track HTMX request performance.

    Helps identify slow endpoints and optimization opportunities.
    """

    def __init__(self) -> None:
        """Initialize with empty request log."""
        self._requests: list[dict[str, Any]] = []
        self._enabled = True

    def enable(self) -> None:
        """Enable performance monitoring."""
        self._enabled = True

    def disable(self) -> None:
        """Disable performance monitoring."""
        self._enabled = False

    def record_request(
        self,
        url: str,
        method: str,
        duration_ms: float,
        size_bytes: int | None = None,
    ) -> None:
        """Record an HTMX request.

        Args:
            url: Request URL
            method: HTTP method
            duration_ms: Request duration in milliseconds
            size_bytes: Response size in bytes
        """
        if not self._enabled:
            return

        self._requests.append(
            {
                "url": url,
                "method": method,
                "duration_ms": duration_ms,
                "size_bytes": size_bytes,
            },
        )

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        if not self._requests:
            return {
                "total_requests": 0,
                "avg_duration_ms": 0,
                "max_duration_ms": 0,
                "total_size_bytes": 0,
            }

        durations = [r["duration_ms"] for r in self._requests]
        sizes = [
            r["size_bytes"] for r in filter(lambda r: r["size_bytes"], self._requests)
        ]

        return {
            "total_requests": len(self._requests),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "total_size_bytes": sum(sizes) if sizes else 0,
            "slow_requests": [r for r in self._requests if r["duration_ms"] > 1000],
        }

    def clear(self) -> None:
        """Clear recorded requests."""
        self._requests.clear()


async def get_htmx_monitor(context: Any | None = None) -> HTMXPerformanceMonitor:
    """Get the global HTMX performance monitor instance."""
    from lexigram.admin.lib.di import get_admin_resolver

    resolver = get_admin_resolver(context)
    return await resolver.resolve(HTMXPerformanceMonitor)


def __getattr__(name: str) -> Any:
    if name == "htmx_monitor":
        raise AttributeError(
            "htmx_monitor is now async. Use: await get_htmx_monitor()",
        )
    raise AttributeError(f"module {__name__} has no attribute {name}")
