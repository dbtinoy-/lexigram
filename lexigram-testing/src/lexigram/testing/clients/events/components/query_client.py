"""Testing client for lexigram-events query operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from lexigram.events import Query, QueryBusProtocol, QueryHandlerProtocol
from lexigram.testing import TestEnvironment


class QueryTestClient:
    """Testing client for lexigram-events query operations.

    Provides high-level testing utilities for query execution and handler testing.

    Example:
        >>> async with EventTestBed() as bed:
        ...     client = QueryTestClient(bed)
        ...     result = await client.execute_query(GetUserQuery(user_id="123"))
        ...     assert result is not None
    """

    def __init__(self, test_bed: TestEnvironment):
        """Initialize the query test client.

        Args:
            test_bed: The test bed providing query infrastructure
        """
        self.test_bed = test_bed
        self._query_bus: QueryBusProtocol | None = None
        self._executed_queries: list[Query] = []
        self._query_results: dict[str, Any] = {}

    @property
    def query_bus(self) -> QueryBusProtocol:
        """Get the query bus from the test bed."""
        if self._query_bus is None:
            self._query_bus = getattr(self.test_bed, "_query_bus", None)
        return cast("QueryBusProtocol", self._query_bus)

    async def execute_query(
        self,
        query: Query,
        expected_success: bool = True,
        expected_result: Any = None,
    ) -> Any:
        """Execute a query and track it.

        Args:
            query: The query to execute
            expected_success: Whether query should succeed
            expected_result: Expected query result

        Returns:
            Query execution result
        """
        # Track the query
        self._executed_queries.append(query)

        try:
            # Execute through the bus
            result = await self.query_bus.send(query)  # type: ignore[attr-defined]
            self._query_results[str(id(query))] = result

            if expected_result is not None and result != expected_result:

                def _raise_expected_result_mismatch() -> None:
                    raise AssertionError(
                        f"Expected query result {expected_result}, got {result}",
                    )

                _raise_expected_result_mismatch()

            return result

        except Exception as e:
            self._query_results[str(id(query))] = e  # Store the exception as result
            if expected_success:
                raise AssertionError(
                    f"Expected query to succeed, but got error: {e}",
                ) from e
            # When expected_success=False, we don't raise - just track the failure
            return None

    async def register_handler(
        self,
        query_type: type[Query],
        handler: QueryHandlerProtocol | Callable,
    ) -> None:
        """Register a query handler.

        Args:
            query_type: The query type to handle
            handler: The handler function or class
        """
        self.query_bus.register(query_type, cast("Callable[..., Any]", handler))  # type: ignore[attr-defined]

    def get_executed_queries(
        self,
        query_type: type[Query] | None = None,
    ) -> list[Query]:
        """Get all executed queries, optionally filtered by type.

        Args:
            query_type: Filter by query type

        Returns:
            List of executed queries
        """
        if query_type:
            return [q for q in self._executed_queries if isinstance(q, query_type)]
        return self._executed_queries.copy()

    def assert_query_executed(
        self,
        query_type: type[Query],
        expected_count: int = 1,
        **filters,
    ) -> list[Query]:
        """Assert that queries of a type were executed.

        Args:
            query_type: The query type to check
            expected_count: Expected number of queries
            **filters: Additional filters for query attributes

        Returns:
            List of matching queries
        """
        queries = self.get_executed_queries(query_type)

        # Apply filters
        if filters:
            queries = [
                query
                for query in queries
                if all(getattr(query, k, None) == v for k, v in filters.items())
            ]

        if len(queries) != expected_count:
            raise AssertionError(
                f"Expected {expected_count} {query_type.__name__} queries, "
                f"found {len(queries)}",
            )

        return queries

    def clear_executed_queries(self) -> None:
        """Clear the executed queries history."""
        self._executed_queries.clear()
        self._query_results.clear()
