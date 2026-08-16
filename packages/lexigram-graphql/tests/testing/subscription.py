"""GraphQL subscription testing utilities.

This module provides utilities for testing GraphQL subscriptions.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import types
from typing import Any

from lexigram.graphql.tests.testing.client import TestResult


class SubscriptionTestClient:
    """Test client for GraphQL subscriptions.

    Executes subscription queries directly against a Strawberry schema and
    surfaces results as an async iterator.  Events can be injected via
    ``publish()`` so that tests can drive the subscription stream without a
    live WebSocket connection.

    Example:
        ```python
        client = SubscriptionTestClient(schema)

        async with client.subscribe("subscription { onMessage { text } }") as results:
            await client.publish("onMessage", {"text": "Hello!"})
            result = await results.__anext__()
            assert result.data["onMessage"]["text"] == "Hello!"
        ```
    """

    def __init__(self, schema: Any, context_value: Any = None) -> None:
        """Initialize the subscription test client.

        Args:
            schema: Strawberry (or graphql-core) GraphQL schema.
            context_value: Optional context to pass to the subscription resolver.
        """
        self._schema = schema
        self._context_value = context_value
        self._event_queues: dict[str, asyncio.Queue[Any]] = {}

    @asynccontextmanager
    async def subscribe(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        context_value: Any = None,
    ) -> AsyncIterator[AsyncIterator[TestResult]]:
        """Subscribe to a GraphQL subscription.

        Executes the subscription against the schema and yields an async
        iterator of :class:`~lexigram.graphql.testing.client.TestResult`
        objects.

        Args:
            query: GraphQL subscription query string.
            variables: Optional query variables.
            context_value: Optional per-request context override.

        Yields:
            Async iterator of TestResult as events arrive.
        """
        ctx = context_value or self._context_value

        # Strawberry 0.200+: schema.execute returns an async generator for subscriptions
        result = await self._schema.execute(
            query,
            variable_values=variables,
            context_value=ctx,
        )

        async def _iter_results() -> AsyncIterator[TestResult]:
            # Handle both async-generator (subscriptions) and single result (error)
            if hasattr(result, "__aiter__"):
                async for item in result:
                    errors = []
                    if hasattr(item, "errors") and item.errors:
                        errors = [{"message": str(e)} for e in item.errors]
                    yield TestResult(
                        data=getattr(item, "data", None),
                        errors=errors,
                        extensions=getattr(item, "extensions", {}) or {},
                    )
            else:
                errors = []
                if hasattr(result, "errors") and result.errors:
                    errors = [{"message": str(e)} for e in result.errors]
                yield TestResult(
                    data=getattr(result, "data", None),
                    errors=errors,
                    extensions=getattr(result, "extensions", {}) or {},
                )

        yield _iter_results()

    async def publish(self, event: str, data: Any) -> None:
        """Publish data into a named event queue.

        Useful together with subscription resolvers that consume from an
        ``asyncio.Queue`` injected via context.

        Args:
            event: Event name (key into the internal queue registry).
            data: Data payload to enqueue.
        """
        queue = self._event_queues.setdefault(event, asyncio.Queue())
        await queue.put(data)

    def get_queue(self, event: str) -> asyncio.Queue[Any]:
        """Get (or create) the asyncio.Queue for a named event.

        Resolvers can consume from this queue to simulate incoming events.

        Args:
            event: Event name.

        Returns:
            The asyncio.Queue for this event.
        """
        return self._event_queues.setdefault(event, asyncio.Queue())

    async def __aenter__(self) -> SubscriptionTestClient:
        """Enter async context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit async context and clean up queues."""
        self._event_queues.clear()


@dataclass
class SubscriptionResult:
    """Result from a subscription.

    Attributes:
        data: Response data.
        errors: List of errors.
        extensions: Response extensions.
    """

    data: dict | None = None
    errors: list[dict] = field(default_factory=list)
    extensions: dict = field(default_factory=dict)


__all__ = [
    "SubscriptionResult",
    "SubscriptionTestClient",
]
