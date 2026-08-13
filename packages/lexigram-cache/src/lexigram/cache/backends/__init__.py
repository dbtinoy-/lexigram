"""
Cache backends for Lexigram Framework.

This package contains backend implementations that wrap infrastructure
drivers, ensuring DRY compliance and consistency.

Note: Database-backed state, secret, and lock stores (previously
``DatabaseBridgeStateStore``, ``DatabaseBridgeSecretStore``, and
``DatabaseBridgeLockStore``) have been moved to ``lexigram-sql`` as
``DatabaseStateStore``, ``DatabaseSecretStore``, and ``DatabaseLockStore``.
Import them from ``lexigram.sql.stores`` instead.
"""

from __future__ import annotations

from lexigram.cache.backends.hash import _compute_hash
from lexigram.cache.backends.memcached.backend import MemcachedCacheBackend
from lexigram.cache.backends.memory.backend import MemoryCacheBackend
from lexigram.cache.backends.redis.backend import RedisCacheBackend

__all__ = [
    "MemcachedCacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "_compute_hash",
]
