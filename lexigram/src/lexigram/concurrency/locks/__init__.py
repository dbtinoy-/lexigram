"""Lock primitives for concurrent access control."""

from __future__ import annotations

from lexigram.concurrency.locks.rwlock import AsyncRWLock

__all__ = ["AsyncRWLock"]
