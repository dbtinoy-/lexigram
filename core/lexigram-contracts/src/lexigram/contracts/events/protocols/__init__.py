"""Event sourcing protocol class definitions (CQRS/ES).

Protocols for event buses, command buses, event stores,
and related patterns.
"""

from __future__ import annotations

from lexigram.contracts.events.protocols.cqrs import (
    CommandBusProtocol as CommandBusProtocol,
)
from lexigram.contracts.events.protocols.cqrs import (
    CommandHandlerProtocol as CommandHandlerProtocol,
)
from lexigram.contracts.events.protocols.cqrs import (
    QueryBusProtocol as QueryBusProtocol,
)
from lexigram.contracts.events.protocols.cqrs import (
    QueryHandlerProtocol as QueryHandlerProtocol,
)
from lexigram.contracts.events.protocols.domain import (
    DomainEventPublisherProtocol as DomainEventPublisherProtocol,
)
from lexigram.contracts.events.protocols.domain import (
    EventBusProtocol as EventBusProtocol,
)
from lexigram.contracts.events.protocols.domain import (
    EventHandlerProtocol as EventHandlerProtocol,
)
from lexigram.contracts.events.protocols.domain import (
    EventMiddlewareProtocol as EventMiddlewareProtocol,
)
from lexigram.contracts.events.protocols.domain import (
    MultiEventHandlerProtocol as MultiEventHandlerProtocol,
)
from lexigram.contracts.events.protocols.projection import (
    IntegrationEventProtocol as IntegrationEventProtocol,
)
from lexigram.contracts.events.protocols.projection import (
    ProjectionProtocol as ProjectionProtocol,
)
from lexigram.contracts.events.protocols.projection import (
    PubSubProtocol as PubSubProtocol,
)
from lexigram.contracts.events.protocols.projection import (
    WebhookSignatureVerifierProtocol as WebhookSignatureVerifierProtocol,
)
from lexigram.contracts.events.protocols.store import (
    AggregateFactoryProtocol as AggregateFactoryProtocol,
)
from lexigram.contracts.events.protocols.store import (
    EventSourcedReadRepositoryProtocol as EventSourcedReadRepositoryProtocol,
)
from lexigram.contracts.events.protocols.store import (
    EventSourcedRepositoryProtocol as EventSourcedRepositoryProtocol,
)
from lexigram.contracts.events.protocols.store import (
    EventStoreProtocol as EventStoreProtocol,
)
from lexigram.contracts.events.protocols.store import (
    SnapshotStoreProtocol as SnapshotStoreProtocol,
)

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
