"""Usage and rankings read service over persisted relay request logs.

Aggregates the ``ai_relay_request_logs`` table into per-user daily usage
and per-model rankings using only generic SQL, so the service works on
any backend.  Cost is summed as a decimal cast at the database and
normalised to a trimmed decimal string on the way out.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from lexigram.contracts.ai.relay import (
    RelayDailyUsage,
    RelayModelRank,
    RelayRequestLogEntry,
    RelayUsageServiceProtocol,
)
from lexigram.primitives import clock

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = ["RelayUsageService"]

_DAILY_USAGE = """
SELECT date(created_at) AS day,
       sum(prompt_tokens) AS prompt_tokens,
       sum(completion_tokens) AS completion_tokens,
       sum(cast(cost AS decimal)) AS cost
FROM ai_relay_request_logs
WHERE user_id = ? AND date(created_at) >= ?
GROUP BY date(created_at)
ORDER BY day
"""

_MODEL_RANK = """
SELECT model,
       sum(completion_tokens) AS completion_tokens,
       count(*) AS request_count,
       sum(cast(cost AS decimal)) AS cost
FROM ai_relay_request_logs
WHERE date(created_at) >= ?
GROUP BY model
ORDER BY completion_tokens DESC
LIMIT ?
"""

_LIST_REQUESTS = """
SELECT request_id, user_id, token_id, endpoint_kind, model, channel_name,
       status, created_at, prompt_tokens, completion_tokens, cost,
       latency_ms, error_code
FROM ai_relay_request_logs
WHERE date(created_at) >= ?
  AND (? IS NULL OR user_id = ?)
  AND (? IS NULL OR token_id = ?)
ORDER BY created_at DESC, request_id DESC
LIMIT ? OFFSET ?
"""


def _cost_text(value: object) -> str:
    """Trim a summed numeric cost to a short decimal string."""
    magnitude = round(float(str(value or "0")), 6)
    return str(Decimal(str(magnitude)))


class RelayUsageService(RelayUsageServiceProtocol):
    """Aggregate reads over ``ai_relay_request_logs``.

    Args:
        db: A connected
            :class:`~lexigram.contracts.data.DatabaseProviderProtocol`
            resolved from the DI container.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db

    async def daily_usage(self, user_id: str, days: int) -> list[RelayDailyUsage]:
        """Aggregate tokens and cost per day for *user_id*.

        Args:
            user_id: The user to aggregate.
            days: Include entries from this many days back (inclusive).

        Returns:
            Daily aggregates ordered by day ascending.
        """
        cutoff = (clock.now().date() - timedelta(days=days - 1)).isoformat()
        result = await self._db.execute_query(_DAILY_USAGE, [user_id, cutoff])
        return [
            RelayDailyUsage(
                day=row["day"],
                prompt_tokens=int(row["prompt_tokens"] or 0),
                completion_tokens=int(row["completion_tokens"] or 0),
                cost=_cost_text(row["cost"]),
            )
            for row in result.rows
        ]

    async def model_rank(self, days: int, limit: int) -> list[RelayModelRank]:
        """Rank models by completion tokens over the window.

        Args:
            days: Include entries from this many days back (inclusive).
            limit: Maximum number of ranked models to return.

        Returns:
            Models ordered by completion tokens descending.
        """
        cutoff = (clock.now().date() - timedelta(days=days - 1)).isoformat()
        result = await self._db.execute_query(_MODEL_RANK, [cutoff, limit])
        return [
            RelayModelRank(
                model=row["model"],
                completion_tokens=int(row["completion_tokens"] or 0),
                request_count=int(row["request_count"] or 0),
                cost=_cost_text(row["cost"]),
            )
            for row in result.rows
        ]

    async def list_requests(
        self,
        days: int,
        page: int,
        page_size: int,
        *,
        user_id: str | None = None,
        token_id: str | None = None,
    ) -> list[RelayRequestLogEntry]:
        """List recent request-log entries, newest first.

        Args:
            days: Include entries from this many days back (inclusive).
            page: One-based result page number.
            page_size: Maximum entries per page.
            user_id: Optional user filter; ``None`` matches all users.
            token_id: Optional token filter; ``None`` matches all tokens.

        Returns:
            The matching entries ordered by time descending.
        """
        cutoff = (clock.now().date() - timedelta(days=days - 1)).isoformat()
        result = await self._db.execute_query(
            _LIST_REQUESTS,
            [
                cutoff,
                user_id,
                user_id,
                token_id,
                token_id,
                page_size,
                (page - 1) * page_size,
            ],
        )
        return [
            RelayRequestLogEntry(
                request_id=row["request_id"],
                user_id=row["user_id"],
                token_id=row["token_id"],
                endpoint_kind=row["endpoint_kind"],
                model=row["model"],
                channel_name=row["channel_name"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                prompt_tokens=int(row["prompt_tokens"] or 0),
                completion_tokens=int(row["completion_tokens"] or 0),
                cost=row["cost"],
                latency_ms=int(row["latency_ms"] or 0),
                error_code=row["error_code"],
            )
            for row in result.rows
        ]
