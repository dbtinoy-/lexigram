"""GraphQL WebSocket Transport for subscriptions.

Provides WebSocket transport implementation using graphql-transport-ws protocol.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from lexigram import serialization as json
from lexigram.graphql.subscriptions.protocol import GQLWSMessageType
from lexigram.graphql.types import SubscriptionInfo
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from lexigram.contracts.graphql.protocols import SubscriptionAuthHandlerProtocol
    from lexigram.contracts.web import WebSocketProtocol

logger = get_logger(__name__)


@dataclass
class SubscriptionConnection:
    """Manages active subscriptions for a WebSocket connection."""

    subscriptions: dict[str, SubscriptionInfo] = field(default_factory=dict)

    def add(self, subscription_id: str, info: SubscriptionInfo) -> None:
        """Add a subscription."""
        self.subscriptions[subscription_id] = info

    def remove(self, subscription_id: str) -> None:
        """Remove a subscription."""
        self.subscriptions.pop(subscription_id, None)

    def get(self, subscription_id: str) -> SubscriptionInfo | None:
        """Get a subscription by ID."""
        return self.subscriptions.get(subscription_id)


class GraphQLWSTransport:
    """WebSocket transport for GraphQL subscriptions.

    Implements the graphql-transport-ws protocol.
    """

    def __init__(
        self,
        execute: Callable[..., Awaitable[Any]] | None = None,
        subscribe: Callable[..., Awaitable[Any]] | None = None,
        connection_init_timeout: float = 10.0,
        keepalive_interval: float = 30.0,
        context_factory: Any | None = None,
        auth_handler: Any | None = None,
        subscription_auth_handler: SubscriptionAuthHandlerProtocol | None = None,
    ):
        """Initialize the transport.

        Args:
            execute: Function to execute GraphQL operations.
            subscribe: Function to subscribe to GraphQL operations.
            connection_init_timeout: Timeout for connection_init in seconds.
            keepalive_interval: Interval for keep-alive messages in seconds.
            context_factory: Optional factory to create GraphQL context.
            auth_handler: Optional handler for connection authentication.
            subscription_auth_handler: Optional per-subscription authorization
                handler.  When provided, :meth:`_handle_subscribe` calls
                :meth:`~lexigram.contracts.graphql.protocols.SubscriptionAuthHandlerProtocol.authorize`
                before any subscription setup.  A ``False`` return value rejects
                the subscription immediately.
        """
        self._execute = execute
        self._subscribe = subscribe
        self.connection_init_timeout = connection_init_timeout
        self.keepalive_interval = keepalive_interval
        self._context_factory = context_factory
        self._auth_handler = auth_handler
        self._subscription_auth_handler = subscription_auth_handler
        self._connection: SubscriptionConnection | None = None
        self._websocket: WebSocketProtocol | None = None
        self._user: Any | None = None
        self._connection_init_received = False
        self._connection_ack_sent = False
        self._background_tasks: set[asyncio.Task] = set()

    async def handle(
        self, websocket: WebSocketProtocol, app: Any | None = None
    ) -> None:
        """Handle a WebSocket connection.

        Args:
            websocket: The WebSocket connection; any object satisfying
                :class:`~lexigram.contracts.http.WebSocketProtocol`
                (e.g. Starlette's ``WebSocket``).
            app: Optional application instance (currently unused; context_factory
                and auth_handler must be injected via constructor).
        """
        self._websocket = websocket
        self._connection = SubscriptionConnection()

        await websocket.accept(subprotocol="graphql-transport-ws")
        logger.debug("WebSocket accepted, starting receive loop")

        # Start keep-alive task
        keepalive_task = asyncio.create_task(self._keepalive())

        try:
            await self._receive_loop()
        except (OSError, RuntimeError) as e:
            logger.error("WebSocket error: %s", e)
            import traceback

            logger.error("Traceback: %s", traceback.format_exc())
        except Exception as e:
            if type(e).__name__ == "WebSocketDisconnect":
                logger.debug("WebSocket disconnected during receive: %s", e)
            else:
                logger.error("WebSocket error: %s", e, exc_info=True)
        finally:
            keepalive_task.cancel()
            await self._cleanup()

    async def _receive_loop(self) -> None:
        """Receive and process messages from the client."""
        if not self._websocket:
            return

        logger.info("===== STARTING RECEIVE LOOP =====")

        while True:
            try:
                data = await self._websocket.receive_text()
                logger.info("WS RECEIVED: {data[:200]}")
            except (OSError, RuntimeError) as e:
                logger.debug("Receive exception: %s", e)
                break
            except Exception as e:
                # WebSocketDisconnect extends Exception directly, not OSError/RuntimeError
                if type(e).__name__ == "WebSocketDisconnect":
                    logger.debug("WebSocket disconnected: %s", e)
                    break
                raise

            try:
                await self._handle_message(json.loads(data))
            except json.JSONDecodeError as e:
                await self._send_error(None, f"Invalid JSON: {e}")
            except (RuntimeError, ValueError, TypeError) as e:
                logger.error("Error handling message: %s", e)
                await self._send_error(None, str(e))

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle a single message from the client.

        Args:
            message: The parsed message.
        """
        msg_type = message.get("type")
        logger.info("WS message: %s", msg_type)
        payload = message.get("payload", {})
        subscription_id = message.get("id")

        if msg_type == GQLWSMessageType.CONNECTION_INIT:
            await self._handle_connection_init(payload)
        elif msg_type == GQLWSMessageType.SUBSCRIBE:
            await self._handle_subscribe(subscription_id, payload)  # type: ignore[arg-type]
        elif msg_type == GQLWSMessageType.COMPLETE:
            await self._handle_complete(subscription_id)  # type: ignore[arg-type]
        elif msg_type == GQLWSMessageType.PING:
            await self._send_message({"type": GQLWSMessageType.PONG})
        elif msg_type == GQLWSMessageType.PONG:
            pass  # Client acknowledged our ping — nothing to do
        elif not self._connection_ack_sent:
            await self._send_error(
                subscription_id,
                f"Unexpected message before connection_ack: {msg_type}",
            )

    async def _handle_connection_init(self, payload: dict[str, Any]) -> None:
        """Handle connection_init message.

        Args:
            payload: The connection payload.
        """
        self._connection_init_received = True
        logger.debug("WS connection_init payload: %s", payload)

        # Authentication via auth_handler if provided
        if self._auth_handler:
            try:
                # authenticate() might return a user object or bool
                auth_result = await self._auth_handler.authenticate(payload)
                if auth_result and not isinstance(auth_result, bool):
                    self._user = auth_result
                    logger.debug("WS auth user set: %s", self._user)
                elif auth_result is True:
                    # Success but no user object returned, check payload for user
                    self._user = payload.get("user")
                    logger.debug("WS auth using payload user: %s", self._user)
            except (RuntimeError, ValueError, TypeError, LookupError) as e:
                logger.warning("WebSocket auth failed: %s", e)
                await self._send_message(
                    {
                        "type": GQLWSMessageType.CONNECTION_ERROR,
                        "payload": {"message": str(e)},
                    }
                )
                if self._websocket:
                    await self._websocket.close(code=4403)
                return

        await self._send_message({"type": GQLWSMessageType.CONNECTION_ACK})
        self._connection_ack_sent = True

    async def _handle_subscribe(
        self,
        subscription_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Handle subscribe message.

        Args:
            subscription_id: The subscription ID.
            payload: The subscribe payload with query, variables, operationName.
        """
        logger.debug(
            "_handle_subscribe called with subscription_id=%s, payload=%s",
            subscription_id,
            payload,
        )
        if not self._connection:
            await self._send_error(subscription_id, "No connection")
            return

        query = payload.get("query")
        variables = payload.get("variables")
        operation_name = payload.get("operationName")

        if not query:
            await self._send_error(subscription_id, "Missing query")
            return

        # Per-subscription authorization check — runs after query validation so
        # the auth handler receives the actual operation details.
        if self._subscription_auth_handler is not None:
            try:
                allowed = await self._subscription_auth_handler.authorize(
                    user=self._user,
                    operation_name=operation_name,
                    query=query,
                )
            except (
                RuntimeError,
                ValueError,
                TypeError,
                LookupError,
                PermissionError,
            ) as e:
                logger.warning("subscription_auth_error", error=str(e))
                await self._send_error(subscription_id, "Authorization error")
                return

            if not allowed:
                await self._send_error(subscription_id, "Unauthorized subscription")
                return

        # Store subscription info
        info = SubscriptionInfo(
            subscription_id=subscription_id,
            operation_name=operation_name,
            query=query,
            variables=variables or {},
        )
        self._connection.add(subscription_id, info)

        try:
            # Check if this is a subscription query
            is_subscription = query.strip().lower().startswith("subscription")
            logger.debug(
                "Handling subscribe, is_subscription: %s, query: %s...",
                is_subscription,
                query[:50],
            )

            # Build context if factory is available
            context_value = None
            logger.debug(
                "Context factory available: %s", self._context_factory is not None
            )
            logger.debug("User to set in context: %s", self._user)
            if self._context_factory:
                from lexigram.graphql.core.context import GraphQLRequest as GQLRequest

                req_obj = GQLRequest(
                    query=query,
                    variables=variables or {},
                    operation_name=operation_name,
                )
                # Correct arguments for ContextFactory.create_context
                metadata: dict[str, Any] = {"raw_request": self._websocket}
                context_value = await self._context_factory.create_context(
                    request=req_obj,
                    user=self._user,
                    metadata=metadata,
                )
                logger.debug("Created context with user: %s", self._user)
            else:
                # Create basic context with user even without factory (must be an object, not dict)
                from lexigram.graphql.core.context import GraphQLContext

                ws_metadata: dict[str, Any] = {"request": self._websocket}
                context_value = GraphQLContext(
                    user=self._user,
                    metadata=ws_metadata,
                )
                logger.debug("Created basic context with user: %s", self._user)

            if is_subscription:
                # Execute the subscription
                if self._subscribe:
                    result = await self._subscribe(
                        query,
                        variable_values=variables,
                        operation_name=operation_name,
                        context_value=context_value,
                    )

                    # Check if it's an iterable (subscription result)
                    if hasattr(result, "__aiter__"):
                        task = asyncio.create_task(
                            self._stream_subscription(subscription_id, result),
                        )
                        self._background_tasks.add(task)
                        task.add_done_callback(self._background_tasks.discard)
                    else:
                        # Immediate result (not a stream)
                        await self._send_next(subscription_id, result)
                        await self._send_complete(subscription_id)
                else:
                    await self._send_error(
                        subscription_id,
                        "Subscription handler not configured",
                    )
            elif self._execute:
                # Execute query/mutation via WebSocket
                result = await self._execute(
                    query,
                    variable_values=variables,
                    operation_name=operation_name,
                    context_value=context_value,
                )
                await self._send_next(subscription_id, result)
                await self._send_complete(subscription_id)
            else:
                await self._send_error(
                    subscription_id,
                    "Execute handler not configured",
                )

        except (RuntimeError, ValueError, TypeError, LookupError) as e:
            logger.error("Subscribe error: %s", e)
            await self._send_error(subscription_id, str(e))
            self._connection.remove(subscription_id)

    async def _stream_subscription(
        self,
        subscription_id: str,
        result: Any,
    ) -> None:
        """Stream subscription results to the client.

        Args:
            subscription_id: The subscription ID.
            result: The subscription result iterator.
        """
        try:
            async for item in result:
                await self._send_next(subscription_id, item)
        except (RuntimeError, ValueError, TypeError, LookupError) as e:
            logger.error("Stream error: %s", e, exc_info=True)
            try:
                await self._send_error(subscription_id, str(e))
            except (OSError, RuntimeError) as send_err:
                logger.debug("subscription_send_error_failed", error=str(send_err))
        finally:
            try:
                await self._send_complete(subscription_id)
            except (OSError, RuntimeError) as complete_err:
                logger.debug(
                    "subscription_send_complete_failed", error=str(complete_err)
                )
            if self._connection:
                self._connection.remove(subscription_id)

    async def _handle_complete(self, subscription_id: str) -> None:
        """Handle complete message (client wants to end subscription).

        Args:
            subscription_id: The subscription ID.
        """
        if self._connection:
            self._connection.remove(subscription_id)

    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a message to the client.

        Args:
            message: The message to send.
        """
        if not self._websocket:
            return
        try:
            await self._websocket.send_json(message)
        except Exception as e:
            if type(e).__name__ == "WebSocketDisconnect":
                logger.debug("WebSocket disconnected while sending: %s", e)
            else:
                raise

    async def _send_next(self, subscription_id: str, data: Any) -> None:
        """Send next message (subscription data).

        Args:
            subscription_id: The subscription ID.
            data: The data to send.
        """
        # Convert ExecutionResult to dict if needed
        payload_data = None
        if data is not None:
            if hasattr(data, "data"):
                payload_data = data.data
            elif hasattr(data, "__dict__"):
                payload_data = data.__dict__
            else:
                payload_data = data

        await self._send_message(
            {
                "id": subscription_id,
                "type": GQLWSMessageType.NEXT,
                "payload": {"data": payload_data} if payload_data else {},
            }
        )

    async def _send_error(self, subscription_id: str | None, error: str) -> None:
        """Send error message.

        Args:
            subscription_id: The subscription ID (may be None for connection errors).
            error: The error message.
        """
        await self._send_message(
            {
                "id": subscription_id,
                "type": GQLWSMessageType.ERROR,
                "payload": {"message": error},
            }
        )

    async def _send_complete(self, subscription_id: str) -> None:
        """Send complete message.

        Args:
            subscription_id: The subscription ID.
        """
        await self._send_message(
            {
                "id": subscription_id,
                "type": GQLWSMessageType.COMPLETE,
            }
        )

    async def _keepalive(self) -> None:
        """Send keep-alive ping messages (graphql-transport-ws protocol)."""
        try:
            while True:
                await asyncio.sleep(self.keepalive_interval)
                if self._websocket and self._connection_ack_sent:
                    await self._send_message({"type": GQLWSMessageType.PING})
        except asyncio.CancelledError:
            pass

    async def _cleanup(self) -> None:
        """Clean up resources on disconnect."""
        if self._connection:
            # Cancel all active subscriptions
            for sub_id in list(self._connection.subscriptions.keys()):
                self._connection.remove(sub_id)
        self._connection = None
        self._websocket = None

    # ------------------------------------------------------------------
    # SubscriptionHandler protocol implementation
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        field_name: str,
        args: dict[str, Any],
        context: Any,
        info: Any,
    ) -> AsyncIterator[Any]:
        """Satisfy the SubscriptionHandler protocol by building and executing a subscription.

        Constructs a minimal GraphQL subscription document from *field_name*
        and *args*, delegates to the underlying ``_subscribe`` callable, and
        returns an async iterator of result values.  Single (non-iterator)
        return values are wrapped in a one-element async iterator for
        protocol uniformity.

        Args:
            field_name: The GraphQL subscription field to subscribe to.
            args: Keyword arguments forwarded as query variables and
                injected into the subscription field call-site.
            context: GraphQL context value passed to the executor.
            info: ResolverProtocol info (ignored at transport level but required
                by the SubscriptionHandler protocol).

        Returns:
            An async iterator that yields subscription event values.

        Raises:
            RuntimeError: If no ``_subscribe`` callable has been configured.
        """
        if self._subscribe is None:
            raise RuntimeError("No subscribe callable configured on GraphQLWSTransport")
        if args:
            var_defs = ", ".join(f"${k}: String" for k in args)
            arg_ref = ", ".join(f"{k}: ${k}" for k in args)
            query = f"subscription Sub({var_defs}) {{ {field_name}({arg_ref}) }}"
        else:
            query = f"subscription {{ {field_name} }}"

        result = await self._subscribe(
            query,
            variable_values=args or None,
            context_value=context,
        )

        if hasattr(result, "__aiter__"):
            return cast("AsyncIterator[Any]", result)

        async def _single_event() -> AsyncIterator[Any]:
            yield result

        return _single_event()


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


__all__ = [
    "GraphQLWSHandler",
    "GraphQLWSTransport",
    "SubscriptionConnection",
    "create_ws_route",
    "graphql_ws_endpoint",
    "logger",
]
