"""
Event testing client and test bed implementation.

This module provides the core testing infrastructure for lexigram-events,
including EventTestClient, CommandTestClient, QueryTestClient, and EventTestBed
for comprehensive event-driven architecture testing.
"""

from __future__ import annotations

# Re-export all testing components for backward compatibility
from lexigram.testing.clients.events.components import (
    CommandTestClient,
    EventTestBed,
    EventTestClient,
    EventTestData,
    QueryTestClient,
)

__all__ = [
    "CommandTestClient",
    "EventTestBed",
    "EventTestClient",
    "EventTestData",
    "QueryTestClient",
]
