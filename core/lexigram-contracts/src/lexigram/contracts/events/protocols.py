"""Event sourcing protocol class definitions (CQRS/ES).

Protocols for event buses, command buses, event stores,
and related patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from lexigram.contracts.core.result import Result
    from lexigram.contracts.exceptions.events import EventError

TAggregate_co = TypeVar("TAggregate_co", covariant=True)

# --- Domain Events ---


@runtime_checkable
class DomainEventPublisherProtocol(Protocol):
    """Protocol for publishing domain events."""

    async def publish(self, event: Any) -> None:
        """Publish a domain event.

        Args:
            event: DomainEvent instance.
        """
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: Any) -> Result[None, EventError]:
        """Handle an event.

        Args:
            event: DomainEvent to handle.

        Returns:
            ``Ok(None)`` on success, ``Err(EventError)`` if handling fails
            in an expected, recoverable way.
        """
        ...


@runtime_checkable
class MultiEventHandlerProtocol(Protocol):
    """Protocol for handlers that handle multiple event types."""

    def handles(self) -> list[type]:
        """Get list of event types handled.

        Returns:
            List of event classes.
        """
        ...

    async def handle(self, event: Any) -> Result[None, EventError]:
        """Handle an event.

        Args:
            event: DomainEvent to handle.

        Returns:
            ``Ok(None)`` on success, ``Err(EventError)`` if handling fails
            in an expected, recoverable way.
        """
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol for event bus implementations.

    The event bus manages event publication and subscription.

        Example:
            ```python
            class InMemoryEventBus:
                async def publish(self, event: DomainEvent) -> "Result[None, EventError]":
                    for handler in self._handlers.get(type(event), []):
                        await handler.handle(event)
                    return Ok(None)

                def subscribe(self, event_type, handler):
                    self._handlers.setdefault(event_type, []).append(handler)
        ```
    """

    async def publish(self, event: Any) -> Result[None, EventError]:
        r"""Publish an event to all subscribers.

        Args:
            event: DomainEvent to publish.

        Returns:
            Ok(None) when the event is successfully enqueued for dispatch.
            Err(EventError) when the event cannot be accepted
            (e.g.\ no handlers registered and the bus requires at least one).
        """
        ...

    def subscribe(self, event_type: type, handler: EventHandlerProtocol) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: Type of event to subscribe to.
            handler: Handler to call when event is published.
        """
        ...

    def unsubscribe(self, event_type: type, handler: EventHandlerProtocol) -> None:
        """Remove a handler subscription for an event type.

        Args:
            event_type: Type of event to unsubscribe from.
            handler: Handler to remove.
        """
        ...


@runtime_checkable
class EventMiddlewareProtocol(Protocol):
    """Protocol for event bus middleware.

    Middleware intercepts event publication, allowing cross-cutting
    concerns like logging, metrics, or error handling to be applied
    transparently.

    The middleware receives the event and a ``next_handler`` coroutine
    that invokes the next middleware (or the actual handlers).  The
    middleware must call ``next_handler`` to continue the chain.

    Example::

        class LoggingMiddleware:
            async def __call__(self, event: Any, next_handler: Any) -> None:
                logger.info("publishing", event_type=type(event).__name__)
                await next_handler(event)
                logger.info("published", event_type=type(event).__name__)
    """

    async def __call__(self, event: Any, next_handler: Any) -> None:
        """Process an event through this middleware.

        Args:
            event: The domain event being published.
            next_handler: Coroutine to call to continue the middleware
                chain.  Must be awaited for the event to reach handlers.
        """
        ...


# --- Commands (CQRS) ---


@runtime_checkable
class CommandHandlerProtocol(Protocol):
    """Protocol for command handlers."""

    async def handle(self, command: Any) -> Any:
        """Handle a command.

        Args:
            command: Command to handle.

        Returns:
            Command result.
        """
        ...


@runtime_checkable
class CommandBusProtocol(Protocol):
    """Protocol for command bus implementations.

    Example:
        ```python
        class CommandBusProtocol:
            async def dispatch(self, command: Command) -> Any:
                handler = self._handlers[type(command)]
                return await handler.handle(command)
        ```
    """

    async def dispatch(self, command: Any) -> Any:
        """Dispatch a command to its handler.

        Args:
            command: Command to dispatch.

        Returns:
            Result from the command handler.
        """
        ...


# --- Queries (CQRS) ---


@runtime_checkable
class QueryHandlerProtocol(Protocol):
    """Protocol for query handlers."""

    async def handle(self, query: Any) -> Any:
        """Handle a query.

        Args:
            query: Query to handle.

        Returns:
            Query result.
        """
        ...


@runtime_checkable
class QueryBusProtocol(Protocol):
    """Protocol for query bus implementations.

    Example:
        ```python
        class QueryBusProtocol:
            async def execute(self, query: Query) -> Any:
                handler = self._handlers[type(query)]
                return await handler.handle(query)
        ```
    """

    async def execute(self, query: Any) -> Any:
        """Execute a query through its handler.

        Args:
            query: Query to execute.

        Returns:
            Query result.
        """
        ...


# --- Event Store ---


@runtime_checkable
class EventStoreProtocol(Protocol):
    """Protocol for event store implementations.

    The event store persists and retrieves domain events.

    Example:
        ```python
        class PostgresEventStore:
            async def append(self, stream_id, events, expected_version=None):
                async with self.db.transaction():
                    for event in events:
                        await self.db.insert("events", event.to_dict())
        ```
    """

    async def append(
        self,
        stream_id: str,
        events: list[Any],
        expected_version: int | None = None,
    ) -> int:
        """Append events to a stream.

        Args:
            stream_id: Unique stream identifier.
            events: List of events to append.
            expected_version: Expected stream version for optimistic concurrency.

        Returns:
            New stream version.

        Raises:
            ConcurrencyError: If expected version doesn't match.
        """
        ...

    async def read(
        self,
        stream_id: str,
        start: int = 0,
        count: int | None = None,
    ) -> list[Any]:
        """Read events from a stream.

        Args:
            stream_id: Unique stream identifier.
            start: Starting position.
            count: Maximum events to read.

        Returns:
            List of events.
        """
        ...

    async def read_all(
        self,
        position: int = 0,
        count: int | None = None,
    ) -> list[Any]:
        """Read events from all streams.

        Args:
            position: Starting global position.
            count: Maximum events to read.

        Returns:
            List of events.
        """
        ...


@runtime_checkable
class SnapshotStoreProtocol(Protocol):
    """Protocol for aggregate snapshot storage."""

    async def save(self, aggregate_id: str, snapshot: Any, version: int) -> None:
        """Save an aggregate snapshot.

        Args:
            aggregate_id: Aggregate identifier.
            snapshot: Aggregate state snapshot.
            version: Aggregate version at snapshot.
        """
        ...

    async def load(self, aggregate_id: str) -> tuple[Any, int] | None:
        """Load the latest snapshot.

        Args:
            aggregate_id: Aggregate identifier.

        Returns:
            Tuple of (snapshot, version) or None if not found.
        """
        ...


# --- Event Sourced RepositoryProtocol ---


@runtime_checkable
class EventSourcedReadRepositoryProtocol(Protocol):
    """Protocol for read-only repository access."""

    async def get(self, aggregate_id: UUID | str) -> Any | None:
        """Load an aggregate by ID."""
        ...

    async def exists(self, aggregate_id: UUID | str) -> bool:
        """Check if an aggregate exists."""
        ...

    async def get_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Any]:
        """Get all aggregates (paginated)."""
        ...


@runtime_checkable
class EventSourcedRepositoryProtocol(EventSourcedReadRepositoryProtocol, Protocol):
    """Protocol for event-sourced repositories (Read/Write)."""

    async def save(self, aggregate: Any) -> None:
        """Save an aggregate."""
        ...


@runtime_checkable
class AggregateFactoryProtocol(Protocol[TAggregate_co]):
    """Factory for creating aggregates."""

    def create(self, aggregate_id: UUID | str) -> TAggregate_co:
        """Create a new aggregate instance.

        Args:
            aggregate_id: Aggregate ID.

        Returns:
            New aggregate instance.
        """
        ...


# --- Projections ---


@runtime_checkable
class ProjectionProtocol(Protocol):
    """ProjectionProtocol protocol for building read models from events."""

    def apply(self, event: Any) -> None:
        """Apply an event to the projection state.

        Args:
            event: Domain event to apply.
        """
        ...


@runtime_checkable
class PubSubProtocol(Protocol):
    """Protocol for publish/subscribe backends.

    Implementations must support publishing messages to topics and
    subscribing handlers to receive messages from topics.
    """

    async def publish(self, topic: str, data: Any) -> None:
        """Publish *data* to *topic*."""
        ...

    async def subscribe(
        self,
        topic: str,
        handler: Any,
    ) -> None:
        """Subscribe *handler* to receive messages from *topic*."""
        ...

    async def unsubscribe(self, topic: str, handler: Any) -> None:
        """Remove *handler* subscription from *topic*."""
        ...


@runtime_checkable
class IntegrationEventProtocol(Protocol):
    """Protocol formalising the bridge between domain events and transactional messaging.

    Any event intended for cross-service communication should satisfy this
    protocol.  Implementations carry all metadata required for reliable,
    idempotent delivery across bounded-context boundaries.

    Attributes:
        event_id: Unique, stable identifier for this event instance (e.g. a UUID4
            string).  Used by consumers for deduplication.
        event_type: The event class name or type discriminator string.  Consumers
            use this to route / deserialise the ``payload``.
        source_service: The bounded context or service that emitted this event
            (e.g. ``"order-service"``).
        correlation_id: Optional distributed-trace correlation identifier that
            links this event to a broader request chain.  ``None`` when tracing
            is not active.
        causation_id: Optional identifier of the event or command that directly
            caused this event to be emitted.  ``None`` for root events.
        payload: The event data as a JSON-serialisable dictionary.  Must not
            contain non-serialisable types (e.g. ``datetime`` objects must be
            ISO-formatted strings).
        occurred_at: UTC timestamp recording when the event occurred in the
            source service.

    Example::

        class UserRegisteredIntegrationEvent:
            event_id: str = field(default_factory=lambda: str(uuid4()))
            event_type: str = "UserRegistered"
            source_service: str = "identity-service"
            correlation_id: str | None = None
            causation_id: str | None = None
            payload: dict[str, Any] = field(default_factory=dict)
            occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """

    event_id: str
    event_type: str
    source_service: str
    correlation_id: str | None
    causation_id: str | None
    payload: dict[str, Any]
    occurred_at: datetime


@runtime_checkable
class WebhookSignatureVerifierProtocol(Protocol):
    """Verifies the authenticity of inbound webhook payloads.

    Implementations must provide both a verification method and a signature
    computation method so callers can independently validate or generate
    signatures without exposing the underlying algorithm.

    The canonical implementation is HMAC-SHA256, but any MAC or asymmetric
    scheme that fulfils this protocol is acceptable.

    Typical usage::

        verifier = HMACWebhookVerifier()
        if not verifier.verify(payload=body, signature=sig_header, secret=secret):
            raise PermissionError("Invalid webhook signature")
    """

    def verify(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Return ``True`` when the signature matches the payload.

        Implementations must use a constant-time comparison to prevent
        timing side-channel attacks.

        Args:
            payload: Raw request body bytes.
            signature: Signature string as received in the request header
                (may include algorithm prefix such as ``"sha256=..."``).
            secret: Shared secret used to compute the expected signature.

        Returns:
            ``True`` if the signature is valid, ``False`` otherwise.
        """
        ...

    def compute_signature(self, payload: bytes, secret: str) -> str:
        """Compute the expected signature for *payload* using *secret*.

        Args:
            payload: Raw request body bytes.
            secret: Shared secret.

        Returns:
            Hex-encoded signature string in the same format that
            :meth:`verify` expects as input.
        """
        ...


__all__ = [
    "AggregateFactoryProtocol",
    "CommandBusProtocol",
    "CommandHandlerProtocol",
    "DomainEventPublisherProtocol",
    "EventBusProtocol",
    "EventHandlerProtocol",
    "EventMiddlewareProtocol",
    "EventSourcedReadRepositoryProtocol",
    "EventSourcedRepositoryProtocol",
    "EventStoreProtocol",
    "IntegrationEventProtocol",
    "MultiEventHandlerProtocol",
    "ProjectionProtocol",
    "PubSubProtocol",
    "QueryBusProtocol",
    "QueryHandlerProtocol",
    "SnapshotStoreProtocol",
    "WebhookSignatureVerifierProtocol",
]
