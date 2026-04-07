"""GraphQL lifecycle domain events.

Typed :class:`~lexigram.contracts.domain.events.DomainEvent` subclasses
published to the :class:`~lexigram.contracts.events.EventBusProtocol` during
GraphQL operation execution and schema lifecycle.  Consumers subscribe to
specific event types via the bus rather than through ad-hoc hook registrations.

Example::

    from lexigram.contracts.events import EventBusProtocol
    from lexigram.graphql.events import AfterExecuteEvent

    class QueryLogger:
        async def handle(self, event: AfterExecuteEvent) -> None:
            logger.info("query_completed", operation=event.execution_context.operation_name)

    bus.subscribe(AfterExecuteEvent, QueryLogger())
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lexigram.contracts.domain.events import DomainEvent

if TYPE_CHECKING:
    from lexigram.graphql.core.execution import ExecutionContextProtocol


@dataclass(frozen=True, init=False)
class BeforeExecuteEvent(DomainEvent):
    """Emitted immediately before a GraphQL operation is sent to Strawberry.

    Subscribers may inspect the execution context (query, variables, user) but
    must NOT modify it — the event is immutable by design.
    """

    execution_context: ExecutionContextProtocol


@dataclass(frozen=True, init=False)
class AfterExecuteEvent(DomainEvent):
    """Emitted after a GraphQL operation completes successfully.

    Contains the execution context with timing information and the raw response.
    """

    execution_context: ExecutionContextProtocol
    result: Any


@dataclass(frozen=True, init=False)
class OnErrorEvent(DomainEvent):
    """Emitted when a GraphQL operation encounters an unhandled exception.

    This is fired for infrastructure-level errors (timeouts, executor crashes),
    not for user-facing field errors which are part of the normal GraphQL response.
    """

    execution_context: ExecutionContextProtocol
    error: Exception


@dataclass(frozen=True, init=False)
class SchemaBuiltEvent(DomainEvent):
    """Emitted after the GraphQL schema is successfully built.

    Consumers may inspect type counts for observability and diagnostics.
    """

    type_count: int


@dataclass(frozen=True, init=False)
class SubscriptionStartedEvent(DomainEvent):
    """Emitted when a GraphQL subscription is established.

    Provides the subscription identifier and operation name for tracking
    and auditing long-lived connections.
    """

    subscription_id: str
    operation: str


__all__ = [
    "AfterExecuteEvent",
    "BeforeExecuteEvent",
    "OnErrorEvent",
    "SchemaBuiltEvent",
    "SubscriptionStartedEvent",
]
