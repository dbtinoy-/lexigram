"""Base message classes for Event Sourcing and CQRS.

Re-exports :class:`~lexigram.contracts.events.messages.Message` and
:class:`~lexigram.contracts.events.messages.MessageMetadata` from
``lexigram.contracts`` so that event-sourcing code has a single, stable
import path within the events package.
"""

from __future__ import annotations

from lexigram.contracts.events.messages import Message, MessageMetadata

__all__ = ["Message", "MessageMetadata"]
