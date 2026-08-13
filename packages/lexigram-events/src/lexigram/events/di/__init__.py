"""Events integration package (M-01).

This package contains the refactored EventsProvider (thin orchestrator)
and its focused sub-providers for framework DI integration.

Sub-providers:
  - :class:`StoreSubProvider`   — EventStoreProtocol + SnapshotStoreProtocol lifecycle
  - :class:`BusSubProvider`     — CommandBusProtocol, QueryBusProtocol, EventBusProtocol lifecycle
  - :class:`HandlerSubProvider` — handler discovery + bus wiring
  - :class:`ManagerSubProvider` — ProjectionManager, SagaManagerProtocol lifecycle

EventsProvider delegates all concerns to the sub-providers above.
"""

from __future__ import annotations

from lexigram.events.di.provider import EventsProvider
from lexigram.events.di.sub_providers.bus_provider import BusSubProvider
from lexigram.events.di.sub_providers.handler_provider import HandlerSubProvider
from lexigram.events.di.sub_providers.manager_provider import ManagerSubProvider
from lexigram.events.di.sub_providers.store_provider import StoreSubProvider

__all__ = [
    "BusSubProvider",
    "EventsProvider",
    "HandlerSubProvider",
    "ManagerSubProvider",
    "StoreSubProvider",
]
