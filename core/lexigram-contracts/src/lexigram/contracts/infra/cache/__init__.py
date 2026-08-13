"""Cache protocols."""

from __future__ import annotations

from lexigram.contracts.core.serialization import AsyncStringSerializerProtocol
from lexigram.contracts.infra.cache.exceptions import (
    CacheError,
    CacheKeyNotFoundError,
    CacheWriteError,
)
from lexigram.contracts.infra.cache.protocols import (
    CacheBackendProtocol,
    CacheHealthCheckerProtocol,
    CacheKeyBuilderProtocol,
    CacheProtectionStrategyProtocol,
    CacheProviderProtocol,
)

__all__ = [
    "AsyncStringSerializerProtocol",
    "CacheBackendProtocol",
    "CacheError",
    "CacheHealthCheckerProtocol",
    "CacheKeyBuilderProtocol",
    "CacheKeyNotFoundError",
    "CacheProtectionStrategyProtocol",
    "CacheProviderProtocol",
    "CacheWriteError",
]
