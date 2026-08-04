"""Database-backed quota backend for LLM routing.

Persists per-provider daily quota state to the ``provider_daily_usage``
table via ``DatabaseProviderProtocol``.  Suitable for multi-process and
production deployments.

All SQL errors are absorbed so that quota tracking failures never interrupt
inference.  If the DB is unreachable, methods return safe defaults
(is_exhausted → False, increment → no-op).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from lexigram.ai.llm.routing.backends._time import end_of_utc_day
from lexigram.ai.llm.routing.types import ProviderUsage
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

__all__ = ["DatabaseQuotaBackend"]

_INCREMENT_SQL = """
INSERT INTO provider_daily_usage (provider, usage_date, success_count)
VALUES ($1, $2, 1)
ON CONFLICT (provider, usage_date)
DO UPDATE SET
    success_count = provider_daily_usage.success_count + 1,
    updated_at    = NOW()
"""

_MARK_EXHAUSTED_SQL = """
INSERT INTO provider_daily_usage (provider, usage_date, is_exhausted, exhausted_until)
VALUES ($1, $2, TRUE, $3)
ON CONFLICT (provider, usage_date)
DO UPDATE SET
    is_exhausted    = TRUE,
    exhausted_until = $3,
    updated_at      = NOW()
"""

_RECORD_ERROR_SQL = """
INSERT INTO provider_daily_usage (provider, usage_date, error_count)
VALUES ($1, $2, 1)
ON CONFLICT (provider, usage_date)
DO UPDATE SET
    error_count = provider_daily_usage.error_count + 1,
    updated_at  = NOW()
"""

_GET_TODAY_SQL = """
SELECT provider, usage_date::text, success_count, error_count, is_exhausted,
       exhausted_until
FROM provider_daily_usage
WHERE provider = $1 AND usage_date = $2
"""

_GET_ALL_TODAY_SQL = """
SELECT provider, usage_date::text, success_count, error_count, is_exhausted,
       exhausted_until
FROM provider_daily_usage
WHERE usage_date = $1
"""


class DatabaseQuotaBackend:
    """PostgreSQL-backed quota backend using ``DatabaseProviderProtocol``.

    Uses UPSERT statements for thread-safe and process-safe concurrent
    updates without application-level locking.

    Example:
        >>> backend = DatabaseQuotaBackend(db=db_provider)
        >>> await backend.increment("groq")
        >>> await backend.is_exhausted("groq")
        False
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialise the database quota backend.

        Args:
            db: Framework database provider (injected from the DI container).
        """
        self._db = db

    def _today(self) -> str:
        """Return today's UTC date as an ISO 8601 string."""
        return date.today().isoformat()

    async def is_exhausted(self, provider: str) -> bool:
        """Return ``True`` when *provider* is quota-exhausted today.

        Args:
            provider: Provider name.

        Returns:
            Whether the provider is currently exhausted; defaults to ``False``
            when the database call fails.
        """
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                row = await conn.fetchrow(_GET_TODAY_SQL, provider, self._today())
                if row is None:
                    return False
                exhausted_until = row["exhausted_until"]
                if exhausted_until is None:
                    return False
                return bool(datetime.now(UTC) < exhausted_until)
        except Exception as e:
            logger.exception(
                "llm.quota.db: is_exhausted query failed for %s", provider, error=str(e)
            )
            return False

    async def increment(self, provider: str) -> None:
        """Record one successful completion for *provider* today.

        Args:
            provider: Provider name.
        """
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                await conn.execute(_INCREMENT_SQL, provider, self._today())
        except Exception as e:
            logger.exception(
                "llm.quota.db: increment failed for %s", provider, error=str(e)
            )

    async def mark_exhausted(
        self, provider: str, *, until: datetime | None = None
    ) -> None:
        """Mark *provider* exhausted until *until*.

        Args:
            provider: Cascade-entry key (``name:model``) or provider name.
            until: Exhaustion expiry; ``None`` means the rest of today (UTC).
        """
        expiry = until or end_of_utc_day()
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                await conn.execute(_MARK_EXHAUSTED_SQL, provider, self._today(), expiry)
                logger.info(
                    "llm.quota.db: %s marked exhausted until %s",
                    provider,
                    expiry.isoformat(),
                )
        except Exception as e:
            logger.exception(
                "llm.quota.db: mark_exhausted failed for %s", provider, error=str(e)
            )

    async def record_error(self, provider: str) -> None:
        """Record a non-exhaustion error for *provider* today.

        Args:
            provider: Provider name.
        """
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                await conn.execute(_RECORD_ERROR_SQL, provider, self._today())
        except Exception as e:
            logger.exception(
                "llm.quota.db: record_error failed for %s", provider, error=str(e)
            )

    async def get_usage(self, provider: str) -> ProviderUsage | None:
        """Return today's usage record for *provider*.

        Args:
            provider: Provider name.

        Returns:
            :class:`ProviderUsage` or ``None`` when not found or on DB error.
        """
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                row = await conn.fetchrow(_GET_TODAY_SQL, provider, self._today())
                if row is None:
                    return None
                return ProviderUsage(
                    provider=row["provider"],
                    usage_date=row["usage_date"],
                    success_count=row["success_count"],
                    error_count=row["error_count"],
                    is_exhausted=row["is_exhausted"],
                    exhausted_until=row["exhausted_until"],
                )
        except Exception as e:
            logger.exception(
                "llm.quota.db: get_usage failed for %s", provider, error=str(e)
            )
            return None

    async def get_all_usage(self) -> list[ProviderUsage]:
        """Return all today's usage records.

        Returns:
            List of :class:`ProviderUsage`; empty list on DB error.
        """
        try:
            async with self._db.scoped_context():
                conn = await self._db.get_scoped_connection()
                rows = await conn.fetch(_GET_ALL_TODAY_SQL, self._today())
                return [
                    ProviderUsage(
                        provider=row["provider"],
                        usage_date=row["usage_date"],
                        success_count=row["success_count"],
                        error_count=row["error_count"],
                        is_exhausted=row["is_exhausted"],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.exception("llm.quota.db: get_all_usage failed", error=str(e))
            return []
