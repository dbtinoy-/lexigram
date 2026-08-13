from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.sql.exceptions import DatabaseConnectionError, DatabaseError, QueryError
from lexigram.sql.middleware.base import QueryMiddleware
from lexigram.sql.middleware.models import QueryContext

logger = get_logger(__name__)


class QueryMiddlewarePipeline:
    """Executes a chain of middleware around database queries."""

    def __init__(self) -> None:
        self._middleware: list[QueryMiddleware] = []

    def add(self, middleware: QueryMiddleware) -> None:
        """Add middleware to the pipeline."""
        self._middleware.append(middleware)

    async def execute(
        self,
        sql: str,
        params: Any,
        execute_fn: Callable[[str, Any], Awaitable[Any]],
    ) -> Any:
        """Execute a query through the middleware pipeline."""
        ctx = QueryContext(sql=sql, params=params)

        for mw in self._middleware:
            await mw.before_query(ctx)

        ctx.start_time = ambient_clock.monotonic()
        try:
            ctx.result = await execute_fn(ctx.sql, ctx.params)
        except (
            DatabaseError,
            QueryError,
            DatabaseConnectionError,
            ValueError,
            TypeError,
        ) as exc:
            ctx.error = exc
            raise
        finally:
            ctx.end_time = ambient_clock.monotonic()
            ctx.duration_ms = (ctx.end_time - ctx.start_time) * 1000

            for mw in reversed(self._middleware):
                try:
                    await mw.after_query(ctx)
                except (
                    DatabaseError,
                    QueryError,
                    DatabaseConnectionError,
                    ValueError,
                    TypeError,
                ):
                    logger.exception("Error in after_query middleware")

        return ctx.result
