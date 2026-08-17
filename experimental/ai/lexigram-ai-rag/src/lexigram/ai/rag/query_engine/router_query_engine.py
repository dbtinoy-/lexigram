"""RouterQueryEngine - Query engine that dispatches to appropriate engine based on router."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from lexigram.contracts.ai.index import (
    QueryEngineError,
    QueryEngineResponse,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class RouterQueryEngine:
    """Query engine that routes queries to different query engines based on a router.

    Uses a router to determine which query engine should handle a given query.

    Example:
        >>> engine = RouterQueryEngine(
        ...     routers={"sql": router, "vector": vector_router},
        ...     query_engines={"sql": sql_engine, "vector": vector_engine},
        ...     default_engine=default_engine,
        ... )
        >>> result = await engine.query("What is in the database?")
    """

    def __init__(
        self,
        routers: dict[str, Any],
        query_engines: dict[str, Any],
        default_engine: Any | None = None,
    ) -> None:
        """Initialize RouterQueryEngine.

        Args:
            routers: Mapping of source names to router instances.
            query_engines: Mapping of source names to query engine instances.
            default_engine: Default query engine to use when routing fails.
        """
        self._routers = routers
        self._query_engines = query_engines
        self._default_engine = default_engine

    async def query(
        self, query: str, **kwargs: Any
    ) -> QueryEngineResponse | QueryEngineError:
        """Process a query by routing to the appropriate query engine.

        Args:
            query: The user's query string.
            **kwargs: Query-specific parameters.

        Returns:
            Ok(QueryEngineResponse) on success.
            Err(QueryEngineError) on failure.
        """
        try:
            route = await self._route_query(query)

            engine = self._query_engines.get(route)
            if engine is None:
                if self._default_engine is not None:
                    engine = self._default_engine
                else:
                    return QueryEngineError(f"No query engine found for route: {route}")

            result = await engine.query(query, **kwargs)
            if isinstance(result, QueryEngineError):
                return result

            return result

        except Exception as e:
            logger.error("router_query_failed", error=str(e))
            return QueryEngineError(f"Query failed: {e}")

    async def astream_query(
        self, query: str, **kwargs: Any
    ) -> AsyncIterator[QueryEngineResponse | QueryEngineError]:
        """Stream query results.

        Args:
            query: The user's query string.
            **kwargs: Query-specific parameters.

        Yields:
            QueryEngineResponse on success, QueryEngineError on failure.
        """
        result = await self.query(query, **kwargs)
        if isinstance(result, QueryEngineError):
            yield result
        else:
            yield result

    async def _route_query(self, query: str) -> str:
        """Route a query to the appropriate source.

        Args:
            query: The query to route.

        Returns:
            Source name to use.
        """
        for source_name, router in self._routers.items():
            try:
                if hasattr(router, "route"):
                    result = await router.route(query)
                elif hasattr(router, "predict"):
                    result = await router.predict(query)
                elif callable(router):
                    result = router(query)
                else:
                    continue

                if result:
                    return source_name
            except Exception as e:
                logger.warning("router_failed", source=source_name, error=str(e))
                continue

        return "default"


__all__ = ["RouterQueryEngine"]
