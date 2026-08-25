"""Cache test bed and client fixtures.

Provides test bed fixtures backed by the available cache backends plus the
matching test client fixtures.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from lexigram.testing.clients.cache.bed import CacheTestBed
from lexigram.testing.clients.cache.client_core import CacheTestClient
from lexigram.testing.clients.cache.fixtures._async import async_fixture

# Test Bed Fixtures


@async_fixture
async def cache_test_bed() -> AsyncGenerator[CacheTestBed, None]:
    """Basic cache test bed with memory backend."""
    async with CacheTestBed(backend_type="memory") as bed:
        yield bed


@async_fixture
async def memory_cache_bed() -> AsyncGenerator[CacheTestBed, None]:
    """Cache test bed with memory backend."""
    async with CacheTestBed(backend_type="memory") as bed:
        yield bed


@async_fixture
async def redis_cache_bed() -> AsyncGenerator[CacheTestBed, None]:
    """Cache test bed with Redis backend."""
    async with CacheTestBed(backend_type="redis") as bed:
        yield bed


# Client Fixtures


@async_fixture
async def cache_client(cache_test_bed: CacheTestBed) -> CacheTestClient:
    """Basic cache test client."""
    return CacheTestClient(cache_test_bed)


@async_fixture
async def memory_cache_client(memory_cache_bed: CacheTestBed) -> CacheTestClient:
    """Cache test client with memory backend."""
    return CacheTestClient(memory_cache_bed)


@async_fixture
async def redis_cache_client(redis_cache_bed: CacheTestBed) -> CacheTestClient:
    """Cache test client with Redis backend."""
    return CacheTestClient(redis_cache_bed)
