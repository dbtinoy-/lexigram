"""Cache lifecycle fixtures.

Provides setup/teardown, pre-populated cache, TTL-enabled cache, metrics
collection, and multi-backend integration fixtures.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from lexigram.cache.config import make_cache_config
from lexigram.cache.providers import CacheProvider  # type: ignore[import-untyped]
from lexigram.logging import get_logger
from lexigram.testing.clients.cache.bed import CacheTestBed
from lexigram.testing.clients.cache.client_core import CacheTestClient
from lexigram.testing.clients.cache.data import CacheTestData
from lexigram.testing.clients.cache.fixtures._async import (
    async_fixture,
    async_fixture_factory,
    pytest_asyncio,
)

# Setup/Teardown Fixtures


@async_fixture_factory(autouse=True, scope="function")
async def cache_cleanup(
    cache_client: CacheTestClient,
) -> AsyncGenerator[None, None]:
    """Automatically clean up cache before and after each test."""
    # Clean up before test
    await cache_client.clear_cache()

    yield

    # Clean up after test
    try:
        await cache_client.clear_cache()
    except (
        RuntimeError,
        OSError,
        ConnectionError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
    ) as e:
        get_logger(__name__).debug(
            "Cache fixture cleanup error (ignored): %s",
            e,
        )  # Ignore cleanup errors


if pytest_asyncio is None:

    @pytest.fixture
    async def populated_cache(
        cache_client: CacheTestClient,
        simple_cache_data: CacheTestData,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache pre-populated with test data."""
        # Populate cache with test data
        for key, item in simple_cache_data.get_all_items().items():
            await cache_client.set_cache_value(key, item["value"], item["ttl"])

        return cache_client  # type: ignore[return-value]

        # Cleanup happens automatically via cache_cleanup fixture

else:

    @async_fixture
    async def populated_cache(
        cache_client: CacheTestClient,
        simple_cache_data: CacheTestData,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache pre-populated with test data."""
        # Populate cache with test data
        for key, item in simple_cache_data.get_all_items().items():
            await cache_client.set_cache_value(key, item["value"], item["ttl"])

        yield cache_client

        # Cleanup happens automatically via cache_cleanup fixture


if pytest_asyncio is None:

    @pytest.fixture
    async def cache_with_ttl(
        cache_client: CacheTestClient,
        short_ttl: int,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache with TTL-enabled entries."""
        test_data = [
            ("ttl_key_1", "value1", short_ttl),
            ("ttl_key_2", "value2", short_ttl * 2),
            ("ttl_key_3", "value3", None),  # No TTL
        ]

        for key, value, ttl in test_data:
            await cache_client.set_cache_value(key, value, ttl)

        return cache_client  # type: ignore[return-value]

else:

    @async_fixture
    async def cache_with_ttl(
        cache_client: CacheTestClient,
        short_ttl: int,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache with TTL-enabled entries."""
        test_data = [
            ("ttl_key_1", "value1", short_ttl),
            ("ttl_key_2", "value2", short_ttl * 2),
            ("ttl_key_3", "value3", None),  # No TTL
        ]

        for key, value, ttl in test_data:
            await cache_client.set_cache_value(key, value, ttl)

        yield cache_client


if pytest_asyncio is None:

    @pytest.fixture
    async def cache_metrics_collector(
        cache_client: CacheTestClient,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache client with metrics collection."""
        # Reset metrics at start
        await cache_client.reset_cache_metrics()

        return cache_client  # type: ignore[return-value]

else:

    @async_fixture
    async def cache_metrics_collector(
        cache_client: CacheTestClient,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache client with metrics collection."""
        # Reset metrics at start
        await cache_client.reset_cache_metrics()

        yield cache_client


# Integration Testing Fixtures


if pytest_asyncio is None:

    @pytest.fixture
    async def multi_backend_cache() -> AsyncGenerator[CacheTestBed, None]:
        """Cache test bed with multiple backends configured."""
        config = {
            "default_backend": "memory",
            "backends": {
                "memory": {"type": "memory", "config": {}},
                "memory_l2": {"type": "memory", "config": {}},
            },
        }

        from lexigram.cache import create_cache_provider
        from lexigram.di.container import Container

        container = Container()
        provider = create_cache_provider(make_cache_config(**config))
        container.singleton(CacheProvider, lambda: provider)

        from lexigram.cache import CacheService

        service = CacheService(provider)
        container.singleton(CacheService, lambda: service)

        # Create test bed manually
        bed = CacheTestBed()
        bed.container = container
        bed._cache_provider = provider
        bed._cache_service = service

        async with bed:
            yield bed

else:

    @async_fixture
    async def multi_backend_cache() -> AsyncGenerator[CacheTestBed, None]:
        """Cache test bed with multiple backends configured."""
        config = {
            "default_backend": "memory",
            "backends": {
                "memory": {"type": "memory", "config": {}},
                "memory_l2": {"type": "memory", "config": {}},
            },
        }

        from lexigram.cache import create_cache_provider
        from lexigram.di.container import Container

        container = Container()
        provider = create_cache_provider(make_cache_config(**config))
        container.singleton(CacheProvider, lambda: provider)

        from lexigram.cache import CacheService

        service = CacheService(provider)
        container.singleton(CacheService, lambda: service)

        # Create test bed manually
        bed = CacheTestBed()
        bed.container = container
        bed._cache_provider = provider
        bed._cache_service = service

        async with bed:
            yield bed
