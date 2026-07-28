"""Query bus implementation.

The QueryBusProtocol dispatches queries to their handlers and supports:
- Single handler per query (enforced)
- Middleware pipeline (caching, logging)
- Explicit handler registration (no service locator)
"""

from __future__ import annotations

import contextlib
from typing import Any, TypeVar

from lexigram.events.buses.base import Bus
from lexigram.events.exceptions import HandlerNotFoundError, QueryExecutionError
from lexigram.events.messages.query import Query
from lexigram.logging import get_logger

logger = get_logger(__name__)


TResult = TypeVar("TResult")


from lexigram.contracts import QueryBusProtocol as QueryBusProtocol


class QueryBusImpl(Bus[Query, Any], QueryBusProtocol):
    """Query bus for dispatching queries.

    Handlers are registered explicitly via ``register()`` or through
    ``HandlerRegistry.register_with_buses()`` during provider registration.

    Example::

        # Queries are automatically routed to handlers
        orders = await bus.execute(GetOrdersByCustomerQuery(
            customer_id="cust-123",
            status="pending"
        ))
    """

    def __init__(
        self,
        middlewares: list[Any] | None = None,
        config: Any | None = None,
    ) -> None:
        """Initialize the query bus."""
        super().__init__(middlewares)
        self._config = config

    async def execute(self, query: Query[TResult]) -> TResult:
        """Execute a query.

        Args:
            query: The query to execute.

        Returns:
            Query result.

        Raises:
            HandlerNotFoundError: If no handler is registered.
            QueryExecutionError: If query execution fails.
        """
        query_type = type(query)

        try:
            handler = await self._resolve_handler(query_type)
        except HandlerNotFoundError as e:
            raise HandlerNotFoundError("Query", query_type.__name__) from e

        from typing import cast

        try:
            return cast("TResult", await self._execute_pipeline(query, handler))
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            if isinstance(e, (HandlerNotFoundError, QueryExecutionError)):
                raise
            with contextlib.suppress(OSError, ValueError, TypeError):
                logger.exception("Query %s failed", query_type.__name__)
            raise QueryExecutionError(
                query_type=query_type.__name__,
                error=str(e),
                cause=e,
            ) from e


__all__ = ["QueryBusImpl"]
