"""
Lexigram Cache - Multi-backend caching system for Lexigram Framework.

This package provides a unified caching API across multiple backends including
in-memory, Redis, and Memcached. It follows the Lexigram Framework's provider
pattern for clean integration and extensibility.

Exports:
    CacheService: Main cache service for DI injection
    CacheProvider: Provider for framework integration
    CacheConfig: Configuration model
    CacheBackendProtocol: Protocol for backend implementations
    BackendType: Enum of supported backends
    CacheError: Base exception for cache errors
"""

from __future__ import annotations

import importlib.metadata

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

from lexigram.cache.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.cache.backends.memcached.backend import MemcachedCacheBackend
    from lexigram.cache.backends.memory.backend import MemoryCacheBackend
    from lexigram.cache.backends.redis.backend import RedisCacheBackend
    from lexigram.cache.config import (
        CacheBackendConfig,
        CacheConfig,
        CacheOperationConfig,
        CacheServiceConfig,
        EnvironmentConfigLoader,
        MemcachedBackendConfig,
        MemoryBackendConfig,
        RedisBackendConfig,
    )
    from lexigram.cache.decorators import cacheable
    from lexigram.cache.di.provider import CacheProvider
    from lexigram.cache.exceptions import (
        CacheBackendError,
        CacheCapacityError,
        CacheConfigurationError,
        CacheConnectionError,
        CacheError,
        CacheInvalidationError,
        CacheKeyError,
        CacheSerializationError,
        CacheStampedeError,
        CacheTimeoutError,
    )
    from lexigram.cache.serialization.compression import CompressingSerializer
    from lexigram.cache.serialization.json import JSONSerializer
    from lexigram.cache.serialization.type_registry import (
        DEFAULT_REGISTRY,
        TypeRegistry,
    )
    from lexigram.cache.service.core import CacheService
    from lexigram.cache.service.decorators import (
        CacheDecorator,
        cache,
        conditional_cache,
        invalidate_cache,
        remember,
    )
    from lexigram.cache.service.request_cache import (
        cache_in_request,
        clear_request_cache,
        get_request_cache,
    )
    from lexigram.cache.stores import RedisLockStore, RedisSecretStore, RedisStateStore
    from lexigram.cache.stores.redis_state import RedisDriver
    from lexigram.cache.types import (
        BackendType,
        CacheEntry,
        CacheHealthResult,
        CacheItem,
        CacheMetrics,
        CacheResult,
        CacheStats,
        CacheStatus,
        CacheStatusHandler,
        DistributedLockInfo,
        TaggedCacheKey,
    )
    from lexigram.contracts.core import HealthStatus
    from lexigram.contracts.infra.cache import (
        AsyncStringSerializerProtocol,
        CacheBackendProtocol,
        CacheHealthCheckerProtocol,
        CacheKeyBuilderProtocol,
        CacheProtectionStrategyProtocol,
    )

_LAZY_IMPORTS = {
    "AutoRenewingLock": "lexigram.cache.locks.auto_renewing",
    "BackendType": "lexigram.cache.types",
    "cacheable": "lexigram.cache.decorators",
    "cache_in_request": "lexigram.cache.service.request_cache",
    "clear_request_cache": "lexigram.cache.service.request_cache",
    "get_request_cache": "lexigram.cache.service.request_cache",
    "CacheBackendProtocol": "lexigram.contracts.cache",
    "CacheBackendConfig": "lexigram.cache.config",
    "CacheBackendError": "lexigram.cache.exceptions",
    "CacheCapacityError": "lexigram.cache.exceptions",
    "CacheConfig": "lexigram.cache.config",
    "CacheConfigurationError": "lexigram.cache.exceptions",
    "CacheConnectionError": "lexigram.cache.exceptions",
    "CacheDecorator": "lexigram.cache.service.decorators",
    "CacheEntry": "lexigram.cache.types",
    "CacheError": "lexigram.cache.exceptions",
    "CacheHealthCheckerProtocol": "lexigram.contracts.cache",
    "CacheHealthResult": "lexigram.cache.types",
    "CacheInvalidationError": "lexigram.cache.exceptions",
    "CacheItem": "lexigram.cache.types",
    "CacheKeyBuilderProtocol": "lexigram.contracts.cache",
    "CacheKeyError": "lexigram.cache.exceptions",
    "CacheMetrics": "lexigram.cache.types",
    "CacheModule": "lexigram.cache.module",
    "CacheOperationConfig": "lexigram.cache.config",
    "CacheProtectionStrategyProtocol": "lexigram.contracts.cache",
    "CacheProvider": "lexigram.cache.di.provider",
    "CacheResult": "lexigram.cache.types",
    "CacheSerializationError": "lexigram.cache.exceptions",
    "CacheService": "lexigram.cache.service.core",
    "CacheServiceConfig": "lexigram.cache.config",
    "CacheStampedeError": "lexigram.cache.exceptions",
    "CacheStats": "lexigram.cache.types",
    "CacheStatus": "lexigram.cache.types",
    "CacheStatusHandler": "lexigram.cache.types",
    "CacheTimeoutError": "lexigram.cache.exceptions",
    "DistributedLockInfo": "lexigram.cache.types",
    "CompressingSerializer": "lexigram.cache.serialization.compression",
    "CostAwareCacheDecision": "lexigram.cache.semantic.cost_decision",
    "DEFAULT_REGISTRY": "lexigram.cache.serialization.type_registry",
    "EnvironmentConfigLoader": "lexigram.cache.config",
    "FaissVectorIndex": "lexigram.cache.semantic.vector_index",
    "HealthStatus": "lexigram.contracts.core",
    "JSONSerializer": "lexigram.cache.serialization.json",
    "MemcachedBackendConfig": "lexigram.cache.config",
    "MemcachedCacheBackend": "lexigram.cache.backends.memcached.backend",
    "MemoryBackendConfig": "lexigram.cache.config",
    "MemoryCacheBackend": "lexigram.cache.backends.memory.backend",
    "RedisBackendConfig": "lexigram.cache.config",
    "RedisCacheBackend": "lexigram.cache.backends.redis.backend",
    "AsyncStringSerializerProtocol": "lexigram.contracts.cache",
    "SemanticCacheStore": "lexigram.cache.semantic.store",
    "TaggedCacheKey": "lexigram.cache.types",
    "TypeRegistry": "lexigram.cache.serialization.type_registry",
    "cache": "lexigram.cache.service.decorators",
    "conditional_cache": "lexigram.cache.service.decorators",
    "invalidate_cache": "lexigram.cache.service.decorators",
    "remember": "lexigram.cache.service.decorators",
    "RedisDriver": "lexigram.cache.stores.redis_state",
    "RedisLockStore": "lexigram.cache.stores.redis_lock",
    "RedisSecretStore": "lexigram.cache.stores.redis_secrets",
    "RedisStateStore": "lexigram.cache.stores.redis_state",
    # Hooks
    "CacheConnectedHook": "lexigram.cache.hooks",
    "CacheDisconnectedHook": "lexigram.cache.hooks",
    "CacheEntryEvictedHook": "lexigram.cache.hooks",
    # Events
    "CacheHitEvent": "lexigram.cache.events",
    "CacheMissEvent": "lexigram.cache.events",
    "CacheEvictedEvent": "lexigram.cache.events",
    "CacheConnectedEvent": "lexigram.cache.events",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> Any:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
