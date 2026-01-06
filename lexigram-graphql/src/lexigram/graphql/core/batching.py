"""GraphQL query batching support.

This module provides batch execution of multiple GraphQL operations
in a single HTTP request.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

from lexigram.graphql.core.context import (
    GraphQLContext,
    GraphQLRequest,
    GraphQLResponse,
)
from lexigram.graphql.exceptions import InputGraphQLError
from lexigram.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BatchResult:
    """Result of batch execution.

    Attributes:
        responses: List of GraphQL responses.
        total_count: Total number of operations.
        success_count: Number of successful operations.
        error_count: Number of failed operations.
    """

    responses: list[GraphQLResponse[Any] | Exception] = field(default_factory=list)
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0


class BatchExecutor:
    """Execute multiple GraphQL operations in a single request.

    Allows clients to send an array of operations in a single HTTP request,
    improving performance for multiple independent queries.

    Example:
        ```python
        executor = GraphQLExecutorProtocol(schema)
        batch_executor = BatchExecutor(executor, max_batch_size=10)

        operations = [
            GraphQLRequest(query="{ user(id: 1) { name } }"),
            GraphQLRequest(query="{ user(id: 2) { name } }"),
        ]

        results = await batch_executor.execute_batch(operations, context)
        ```
    """

    def __init__(
        self,
        executor: Any,  # GraphQLExecutorProtocol
        max_batch_size: int = 10,
    ):
        """Initialize the batch executor.

        Args:
            executor: The GraphQL executor to use.
            max_batch_size: Maximum number of operations per batch.
        """
        self._executor = executor
        self._max_batch_size = max_batch_size

    @property
    def max_batch_size(self) -> int:
        """Get maximum batch size."""
        return self._max_batch_size

    async def execute_batch(
        self,
        operations: list[GraphQLRequest],
        context: GraphQLContext,
    ) -> BatchResult:
        """Execute operations as a batch.

        Args:
            operations: List of GraphQL requests to execute.
            context: GraphQL context.

        Returns:
            BatchResult with all responses.

        Raises:
            InputGraphQLError: If batch size exceeds limit.
        """
        if len(operations) > self._max_batch_size:
            raise InputGraphQLError(
                message=f"Batch size {len(operations)} exceeds maximum of {self._max_batch_size}",
            )

        if not operations:
            return BatchResult()

        # Create tasks for concurrent execution
        tasks = []
        for op in operations:
            # Create a copy of context for each operation
            op_context = context.copy() if hasattr(context, "copy") else context
            task = self._execute_single(op, op_context)
            tasks.append(task)

        # Execute all operations concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and errors
        success_count = sum(1 for r in responses if not isinstance(r, Exception))
        error_count = len(responses) - success_count

        return BatchResult(
            responses=cast("list[GraphQLResponse[Any] | Exception]", responses),
            total_count=len(operations),
            success_count=success_count,
            error_count=error_count,
        )

    async def _execute_single(
        self,
        operation: GraphQLRequest,
        context: GraphQLContext,
    ) -> GraphQLResponse[Any] | Exception:
        """Execute a single operation.

        Args:
            operation: GraphQL request.
            context: GraphQL context.

        Returns:
            GraphQL response or exception.
        """
        try:
            # Create a new execution context for this operation
            from lexigram.graphql.core.execution import ExecutionContextProtocol

            exec_context = ExecutionContextProtocol(context=context)
            return cast(
                "GraphQLResponse[Any]",
                await self._executor._execute_internal(exec_context),
            )
        except Exception as e:  # noqa: BLE001 — batch operations must not raise; exception is returned as the batch result
            logger.exception("Batch operation failed")
            return e


def is_batch_request(body: Any) -> bool:
    """Detect if a request body is a batch operation.

    Args:
        body: The request body (parsed JSON).

    Returns:
        True if the body is a list of operations.
    """
    return isinstance(body, list)


def parse_batch_request(body: Any) -> list[GraphQLRequest]:
    """Parse a batch request body into GraphQLRequests.

    Args:
        body: The request body (list of operations).

    Returns:
        List of GraphQLRequest objects.
    """
    requests = []
    for item in body:
        if isinstance(item, dict):
            requests.append(
                GraphQLRequest(
                    query=item.get("query"),
                    variables=item.get("variables"),
                    operation_name=item.get("operationName"),
                )
            )
    return requests


__all__ = [
    "BatchExecutor",
    "BatchResult",
    "is_batch_request",
    "parse_batch_request",
]
