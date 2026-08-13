from __future__ import annotations

from collections import defaultdict
from typing import Any

from lexigram.logging import get_logger
from lexigram.sql.middleware.base import QueryMiddleware
from lexigram.sql.middleware.models import QueryContext

logger = get_logger(__name__)


class SlowQueryLogger(QueryMiddleware):
    """Logs queries that exceed a duration threshold."""

    def __init__(
        self,
        threshold_ms: float = 100.0,
        *,
        log_params: bool = False,
    ) -> None:
        self.threshold_ms = threshold_ms
        self.log_params = log_params

    async def after_query(self, ctx: QueryContext) -> None:
        if ctx.duration_ms >= self.threshold_ms:
            msg = "SLOW QUERY (%.1fms): %s"
            args: list[Any] = [ctx.duration_ms, ctx.sql[:500]]
            if self.log_params:
                msg += " | params=%s"
                args.append(ctx.params)
            logger.warning(msg, *args)


class QueryMetricsCollector(QueryMiddleware):
    """Collects query execution metrics in memory."""

    def __init__(self) -> None:
        self._metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_ms": 0.0,
                "min_ms": float("inf"),
                "max_ms": 0.0,
                "errors": 0,
            },
        )
        self._total_queries = 0
        self._total_errors = 0

    async def after_query(self, ctx: QueryContext) -> None:
        pattern = ctx.sql[:100].strip()
        self._total_queries += 1

        entry = self._metrics[pattern]
        entry["count"] += 1
        entry["total_ms"] += ctx.duration_ms
        entry["min_ms"] = min(entry["min_ms"], ctx.duration_ms)
        entry["max_ms"] = max(entry["max_ms"], ctx.duration_ms)

        if ctx.error:
            entry["errors"] += 1
            self._total_errors += 1

    def get_stats(self) -> dict[str, Any]:
        """Get aggregated query statistics."""
        top_queries = sorted(
            self._metrics.items(),
            key=lambda x: x[1]["total_ms"],
            reverse=True,
        )[:20]

        return {
            "total_queries": self._total_queries,
            "total_errors": self._total_errors,
            "top_slow_queries": [
                {
                    "pattern": pattern,
                    "count": m["count"],
                    "avg_ms": round(m["total_ms"] / m["count"], 2),
                    "min_ms": round(m["min_ms"], 2),
                    "max_ms": round(m["max_ms"], 2),
                    "errors": m["errors"],
                }
                for pattern, m in top_queries
            ],
        }

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._metrics.clear()
        self._total_queries = 0
        self._total_errors = 0


class QueryAuditLogger(QueryMiddleware):
    """Logs all write operations for audit purposes."""

    WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP")

    async def after_query(self, ctx: QueryContext) -> None:
        upper_sql = ctx.sql.strip().upper()
        if any(upper_sql.startswith(p) for p in self.WRITE_PREFIXES):
            logger.info(
                "AUDIT [%.1fms]: %s",
                ctx.duration_ms,
                ctx.sql[:300],
            )
