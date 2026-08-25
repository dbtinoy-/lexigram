"""Pytest fixtures for lexigram-cache testing.

This package provides comprehensive pytest fixtures for various cache testing
scenarios, including different backends, data types, TTL configurations, and
error conditions. Concerns are grouped into submodules — ``beds`` (test beds
and clients), ``data`` (keys, values, TTLs, backends), ``scenarios`` (error
and failure scenarios), and ``lifecycle`` (cleanup, populated caches,
metrics) — and re-exported here.
"""

from __future__ import annotations

from lexigram.testing.clients.cache.bed import CacheTestBed as CacheTestBed
from lexigram.testing.clients.cache.client_core import (
    CacheTestClient as CacheTestClient,
)
from lexigram.testing.clients.cache.data import CacheTestData as CacheTestData
from lexigram.testing.clients.cache.fixtures.beds import (
    cache_client as cache_client,
)
from lexigram.testing.clients.cache.fixtures.beds import (
    cache_test_bed as cache_test_bed,
)
from lexigram.testing.clients.cache.fixtures.beds import (
    memory_cache_bed as memory_cache_bed,
)
from lexigram.testing.clients.cache.fixtures.beds import (
    memory_cache_client as memory_cache_client,
)
from lexigram.testing.clients.cache.fixtures.beds import (
    redis_cache_bed as redis_cache_bed,
)
from lexigram.testing.clients.cache.fixtures.beds import (
    redis_cache_client as redis_cache_client,
)
from lexigram.testing.clients.cache.fixtures.data import (
    cache_test_data as cache_test_data,
)
from lexigram.testing.clients.cache.fixtures.data import (
    complex_cache_data as complex_cache_data,
)
from lexigram.testing.clients.cache.fixtures.data import (
    complex_keys as complex_keys,
)
from lexigram.testing.clients.cache.fixtures.data import (
    concurrent_test_keys as concurrent_test_keys,
)
from lexigram.testing.clients.cache.fixtures.data import (
    dict_values as dict_values,
)
from lexigram.testing.clients.cache.fixtures.data import (
    list_values as list_values,
)
from lexigram.testing.clients.cache.fixtures.data import (
    long_ttl as long_ttl,
)
from lexigram.testing.clients.cache.fixtures.data import (
    medium_ttl as medium_ttl,
)
from lexigram.testing.clients.cache.fixtures.data import (
    memory_backend as memory_backend,
)
from lexigram.testing.clients.cache.fixtures.data import (
    mixed_values as mixed_values,
)
from lexigram.testing.clients.cache.fixtures.data import (
    namespaced_keys as namespaced_keys,
)
from lexigram.testing.clients.cache.fixtures.data import (
    performance_test_data as performance_test_data,
)
from lexigram.testing.clients.cache.fixtures.data import (
    redis_backend as redis_backend,
)
from lexigram.testing.clients.cache.fixtures.data import (
    short_ttl as short_ttl,
)
from lexigram.testing.clients.cache.fixtures.data import (
    simple_cache_data as simple_cache_data,
)
from lexigram.testing.clients.cache.fixtures.data import (
    simple_keys as simple_keys,
)
from lexigram.testing.clients.cache.fixtures.data import (
    string_values as string_values,
)
from lexigram.testing.clients.cache.fixtures.lifecycle import (
    cache_cleanup as cache_cleanup,
)
from lexigram.testing.clients.cache.fixtures.lifecycle import (
    cache_metrics_collector as cache_metrics_collector,
)
from lexigram.testing.clients.cache.fixtures.lifecycle import (
    cache_with_ttl as cache_with_ttl,
)
from lexigram.testing.clients.cache.fixtures.lifecycle import (
    multi_backend_cache as multi_backend_cache,
)
from lexigram.testing.clients.cache.fixtures.lifecycle import (
    populated_cache as populated_cache,
)
from lexigram.testing.clients.cache.fixtures.scenarios import (
    backend_failure_scenarios as backend_failure_scenarios,
)
from lexigram.testing.clients.cache.fixtures.scenarios import (
    cache_error_scenarios as cache_error_scenarios,
)

__all__ = [
    "CacheTestBed",
    "CacheTestClient",
    "CacheTestData",
    "backend_failure_scenarios",
    "cache_cleanup",
    "cache_client",
    "cache_error_scenarios",
    "cache_metrics_collector",
    "cache_test_bed",
    "cache_test_data",
    "cache_with_ttl",
    "complex_cache_data",
    "complex_keys",
    "concurrent_test_keys",
    "dict_values",
    "list_values",
    "long_ttl",
    "medium_ttl",
    "memory_backend",
    "memory_cache_bed",
    "memory_cache_client",
    "mixed_values",
    "multi_backend_cache",
    "namespaced_keys",
    "performance_test_data",
    "populated_cache",
    "redis_backend",
    "redis_cache_bed",
    "redis_cache_client",
    "short_ttl",
    "simple_cache_data",
    "simple_keys",
    "string_values",
]
