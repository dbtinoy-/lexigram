from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
from lexigram.logging import get_logger
from lexigram.ui import (
    Card,
    Divider,
    EmptyState,
    Grid,
    StatCard,
    el,
    render_to_string,
)

logger = get_logger(__name__)


class CacheStatsPage:
    """Detailed cache statistics for /admin/cache/stats."""

    def __init__(self, cache: CacheBackendProtocol | None = None) -> None:
        self._cache = cache

    async def handle(self, request: Any) -> HTMLResponse:
        if self._cache is None:
            html = render_to_string(
                EmptyState(
                    title="Cache Unavailable",
                    message="The cache backend could not be resolved.",
                    icon="database",
                ),
            )
            return HTMLResponse(html)
        try:
            health = await self._cache.health_check()
            healthy = health.is_healthy()
            latency = int(health.duration_ms)
            details = health.details or {}
            metrics = details.get("metrics", {}) if isinstance(details, dict) else {}
        except Exception:
            healthy = False
            latency = 0
            metrics = {}

        hit_rate = metrics.get("hit_rate", "N/A")
        if isinstance(hit_rate, (int, float)):
            hit_rate = f"{hit_rate * 100:.0f}%"
        total_ops = metrics.get("total_operations", "N/A")
        hits = metrics.get("hits", "N/A")
        misses = metrics.get("misses", "N/A")
        sets = metrics.get("sets", "N/A")
        deletes = metrics.get("deletes", "N/A")
        errors = metrics.get("errors", "N/A")
        avg_latency = metrics.get("avg_latency_ms", 0)
        if isinstance(avg_latency, (int, float)):
            avg_latency = f"{avg_latency:.1f}ms"

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Cache Statistics",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Detailed performance metrics for the cache backend.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Backend",
                        value="OK" if healthy else "Down",
                        icon="activity",
                        delta=f"{latency}ms" if healthy else None,
                        delta_color="green",
                    ),
                    StatCard(
                        label="Hit Ratio",
                        value=str(hit_rate),
                        icon="trending-up",
                    ),
                    StatCard(
                        label="Operations",
                        value=str(total_ops),
                        icon="database",
                    ),
                    StatCard(
                        label="Avg Latency",
                        value=str(avg_latency),
                        icon="clock",
                    ),
                    cols={"default": 1, "lg": 4},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Backend Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Backend Type",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                type(self._cache).__name__,
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Status",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Healthy" if healthy else "Unhealthy",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Latency",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                f"{latency}ms",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Avg Latency",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(avg_latency),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Hit Ratio",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(hit_rate),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Hits",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(hits),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Misses",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(misses),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Sets",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(sets),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Deletes",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(deletes),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Errors",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(errors),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        )
                    ),
                ),
                class_="p-6",
            ),
        )

        return HTMLResponse(html)
