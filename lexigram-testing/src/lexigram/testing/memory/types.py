"""Type definitions for the memory subsystem.

Re-exports ``OutboxStatus`` and ``OutboxEntry`` from their canonical
home in ``lexigram.memory.outbox`` for convenient top-level access.
"""

from __future__ import annotations

from lexigram.testing.memory.outbox import OutboxEntry as OutboxEntry
from lexigram.testing.memory.outbox import OutboxStatus as OutboxStatus

__all__ = [
    "OutboxEntry",
    "OutboxStatus",
]
