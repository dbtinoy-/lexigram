"""Distributed locking utilities for Lexigram cache.

Provides distributed locks with automatic TTL renewal.
"""

from __future__ import annotations

from lexigram.cache.locks.distributed import (
    DistributedLockInfo,
    DistributedLockProtocol,
)
from lexigram.cache.locks.manager import LockManager

__all__ = [
    "DistributedLockInfo",
    "DistributedLockProtocol",
    "LockManager",
]
