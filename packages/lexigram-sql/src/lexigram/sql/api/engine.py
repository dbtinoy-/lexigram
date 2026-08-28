"""QueryEngine implementation for lexigram-sql."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.sql.api.protocols import DatabaseProviderProtocol


@inject
class QueryEngine:
    """Convenience wrapper for raw SQL queries via DatabaseService.

    This is a concrete implementation, not a protocol.
    Inject ``DatabaseProviderProtocol`` directly for more control.
    """

    def __init__(self, provider: DatabaseProviderProtocol):
        self.provider = provider

    async def execute(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
        fetch: bool = True,
    ) -> Any:
        async with self.provider.get_connection() as conn:
            result = await conn.execute(sql, params)
            if fetch:
                try:
                    return result.fetchall()
                except (AttributeError, TypeError) as e:
                    # Result may not support fetching; return None for convenience
                    get_logger(__name__).debug(
                        "Fetch all not available on result: %s",
                        e,
                        exc_info=True,
                    )
                return None
            return result

    async def fetchone(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, Any] | None:
        rows = await self.execute(sql, params, fetch=True)
        return rows[0] if rows else None

    async def fetchall(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, Any]]:
        rows = await self.execute(sql, params, fetch=True)
        return rows or []

    async def scalar(self, sql: str, params: tuple[object, ...] | None = None) -> Any:
        async with self.provider.get_connection() as conn:
            result = await conn.execute(sql, params)
            if hasattr(result, "scalar"):
                return result.scalar()
            if hasattr(result, "fetchone"):
                row = result.fetchone()
                if row:
                    # attempt common column names
                    return row.get("count") if isinstance(row, dict) else None
            return None


__all__ = ["QueryEngine"]
