"""GraphQL WebSocket Transport for subscriptions.

Provides WebSocket transport implementation using graphql-transport-ws protocol.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from lexigram import serialization as json
from lexigram.graphql.subscriptions.protocol import GQLWSMessageType
from lexigram.graphql.subscriptions.transport._transport import GraphQLWSTransport
from lexigram.graphql.types import SubscriptionInfo
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from lexigram.contracts.graphql.protocols import SubscriptionAuthHandlerProtocol
    from lexigram.contracts.web import WebSocketProtocol

logger = get_logger(__name__)


async def graphql_ws_endpoint(websocket: Any) -> None:
    """ASGI-compatible endpoint for GraphQL WebSocket connections.

    This is a simple endpoint that can be used with Starlette.
    For production use, configure with proper execute/subscribe handlers.

    Example:
        from starlette.routing import Route
        from lexigram.graphql import constants as const

        async def get_transport():
            from lexigram.graphql.schema import build_schema
            # Configure with your schema
            return GraphQLWSTransport(
                execute=execute_fn,
                subscribe=subscribe_fn,
            )

        routes = [
            Route(const.DEFAULT_SUBSCRIPTIONS_PATH, graphql_ws_endpoint),
        ]
    """
    transport = GraphQLWSTransport()
    await transport.handle(websocket)


def create_ws_route(path: str) -> Any:
    """Create a WebSocket route for GraphQL subscriptions.

    Returns a Starlette ``Route`` when ``starlette`` is installed.  The return
    type is ``Any`` so callers are not forced to depend on Starlette directly.

    Args:
        path: The WebSocket path.

    Returns:
        A Starlette Route object.
    """
    from starlette.routing import Route  # deferred — Starlette is optional

    return Route(path, graphql_ws_endpoint)


class GraphQLWSHandler:
    """Handler class for GraphQL WebSocket subscriptions.

    This class provides a more configurable way to handle subscriptions.
    """

    def __init__(
        self,
        execute: Callable[..., Awaitable[Any]] | None = None,
        subscribe: Callable[..., Awaitable[Any]] | None = None,
        connection_init_timeout: float = 10.0,
        keepalive_interval: float = 30.0,
        context_factory: Any | None = None,
        auth_handler: Any | None = None,
    ):
        """Initialize the handler.

        Args:
            execute: Function to execute GraphQL operations.
            subscribe: Function to subscribe to GraphQL operations.
            connection_init_timeout: Timeout for connection_init in seconds.
            keepalive_interval: Interval for keep-alive messages in seconds.
            context_factory: Optional factory to create GraphQL context.
            auth_handler: Optional handler for connection authentication.
        """
        self._transport = GraphQLWSTransport(
            execute=execute,
            subscribe=subscribe,
            connection_init_timeout=connection_init_timeout,
            keepalive_interval=keepalive_interval,
            context_factory=context_factory,
            auth_handler=auth_handler,
        )

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Handle WebSocket connection.

        Args:
            scope: ASGI scope
            receive: ASGI receive
            send: ASGI send
        """
        from starlette.websockets import WebSocket

        websocket = WebSocket(scope=scope, receive=receive, send=send)
        await self._transport.handle(websocket, app=scope.get("app"))

    @classmethod
    def create_from_schema(
        cls,
        schema: Any,
        execute: Callable[..., Awaitable[Any]] | None = None,
        context_factory: Any | None = None,
        auth_handler: Any | None = None,
    ) -> GraphQLWSHandler:
        """Create a handler from a Strawberry schema.

        Args:
            schema: The Strawberry schema.
            execute: Optional custom execute function.
            context_factory: Optional factory to create GraphQL context.
            auth_handler: Optional handler for connection authentication.

        Returns:
            A configured GraphQLWSHandler.
        """
        # Get execute/subscribe from schema if not provided
        if execute is None and hasattr(schema, "execute"):
            execute = schema.execute

        subscribe = None
        if hasattr(schema, "subscribe"):
            subscribe = schema.subscribe

        return cls(
            execute=execute,
            subscribe=subscribe,
            context_factory=context_factory,
            auth_handler=auth_handler,
        )
