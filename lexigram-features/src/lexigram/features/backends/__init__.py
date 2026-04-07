"""Concrete feature-flag backend implementations.

Backends:
    AbstractFlagProvider: Rich abstract base class with full evaluation logic.
    LocalProvider: In-memory, code-defined flag store.
    EnvProvider: Reads flags from environment variables.
    ChainedProvider: Layered lookup across multiple providers.
    MemoryProvider: Lightweight test double with override support.
    CacheBackendFlagProvider: Cache-backed provider (Redis, Memcached, etc.).
"""

from __future__ import annotations

from lexigram.features.backends.base import AbstractFlagProvider
from lexigram.features.backends.cache import CacheBackendFlagProvider
from lexigram.features.backends.chained import ChainedProvider
from lexigram.features.backends.env import EnvProvider
from lexigram.features.backends.local import LocalProvider
from lexigram.features.backends.testing import MemoryProvider

__all__ = [
    "AbstractFlagProvider",
    "CacheBackendFlagProvider",
    "ChainedProvider",
    "EnvProvider",
    "LocalProvider",
    "MemoryProvider",
]
