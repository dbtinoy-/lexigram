"""Buses module for Event Sourcing and CQRS.

This module provides the message bus implementations:
- CommandBusImpl: For dispatching commands (single handler)
- QueryBusImpl: For dispatching queries (single handler)
- EventBusImpl: For publishing events (multiple handlers)
"""

from __future__ import annotations

from lexigram.events.buses.base import Bus, MiddlewareFunc
from lexigram.events.buses.command import CommandBusImpl
from lexigram.events.buses.event import EventBusImpl
from lexigram.events.buses.query import QueryBusImpl

__all__ = [
    "Bus",
    "CommandBusImpl",
    "EventBusImpl",
    "MiddlewareFunc",
    "QueryBusImpl",
]
