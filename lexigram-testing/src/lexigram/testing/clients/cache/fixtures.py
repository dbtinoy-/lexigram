"""
Pytest fixtures for lexigram-cache testing.

This module provides comprehensive pytest fixtures for various cache testing
scenarios, including different backends, data types, TTL configurations,
and error conditions.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any, ParamSpec, TypeVar

import pytest

from lexigram.cache.config import make_cache_config
from lexigram.cache.providers import CacheProvider  # type: ignore[import-untyped]
from lexigram.logging import get_logger
from lexigram.testing.clients.cache.client import (
    CacheTestBed,
    CacheTestClient,
    CacheTestData,
)

pytest_asyncio: Any | None
try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None


P = ParamSpec("P")
R = TypeVar("R")
_async_fixture: Callable[..., Any] = (
    pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
)

# Test Bed Fixtures


@_async_fixture
async def cache_test_bed() -> AsyncGenerator[CacheTestBed, None]:
    """Basic cache test bed with memory backend."""
    async with CacheTestBed(backend_type="memory") as bed:
        yield bed


@_async_fixture
async def memory_cache_bed() -> AsyncGenerator[CacheTestBed, None]:
    """Cache test bed with memory backend."""
    async with CacheTestBed(backend_type="memory") as bed:
        yield bed


@_async_fixture
async def redis_cache_bed() -> AsyncGenerator[CacheTestBed, None]:
    """Cache test bed with Redis backend."""
    async with CacheTestBed(backend_type="redis") as bed:
        yield bed


# Client Fixtures


@_async_fixture
async def cache_client(cache_test_bed: CacheTestBed) -> CacheTestClient:
    """Basic cache test client."""
    return CacheTestClient(cache_test_bed)


@_async_fixture
async def memory_cache_client(memory_cache_bed: CacheTestBed) -> CacheTestClient:
    """Cache test client with memory backend."""
    return CacheTestClient(memory_cache_bed)


@_async_fixture
async def redis_cache_client(redis_cache_bed: CacheTestBed) -> CacheTestClient:
    """Cache test client with Redis backend."""
    return CacheTestClient(redis_cache_bed)


# Data Fixtures


@pytest.fixture
def cache_test_data() -> CacheTestData:
    """Basic cache test data."""
    return CacheTestData.create_simple("test")


@pytest.fixture
def simple_cache_data() -> CacheTestData:
    """Simple cache test data with basic types."""
    return CacheTestData.create_simple("simple")


@pytest.fixture
def complex_cache_data() -> CacheTestData:
    """Complex cache test data with nested structures."""
    return CacheTestData.create_complex("complex")


# Backend Fixtures


@pytest.fixture
def memory_backend() -> Any:
    """Memory cache backend instance."""
    from lexigram.cache import MemoryCacheBackend

    return MemoryCacheBackend()


@pytest.fixture
def redis_backend() -> dict[str, Any]:
    """Redis cache backend configuration."""
    # Note: This is configuration, not an actual backend instance
    return {"type": "redis", "config": {"host": "localhost", "port": 6379, "db": 1}}


# TTL Fixtures


@pytest.fixture
def short_ttl() -> int:
    """Short TTL for testing (1 second)."""
    return 1


@pytest.fixture
def medium_ttl() -> int:
    """Medium TTL for testing (30 seconds)."""
    return 30


@pytest.fixture
def long_ttl() -> int:
    """Long TTL for testing (300 seconds)."""
    return 300


# Key Fixtures


@pytest.fixture
def simple_keys() -> list[str]:
    """Simple cache keys."""
    return ["key1", "key2", "key3", "test_key", "another_key"]


@pytest.fixture
def complex_keys() -> list[str]:
    """Complex cache keys with special characters."""
    return [
        "user:123:profile",
        "cache:item:456:data",
        "namespace:key:with:colons",
        "key with spaces",
        "key-with-dashes",
    ]


@pytest.fixture
def namespaced_keys() -> list[str]:
    """Namespaced cache keys."""
    return [
        "app:user:1",
        "app:user:2",
        "app:product:100",
        "app:product:200",
        "session:abc123",
        "session:def456",
    ]


# Value Fixtures


@pytest.fixture
def string_values() -> list[str]:
    """String cache values."""
    return ["hello world", "test value", "another string", "cache me", "data"]


@pytest.fixture
def dict_values() -> list[dict[str, Any]]:
    """Dictionary cache values."""
    return [
        {"name": "Alice", "age": 30, "city": "New York"},
        {"product": "Widget", "price": 19.99, "in_stock": True},
        {"user_id": 123, "preferences": {"theme": "dark", "notifications": True}},
        {"metadata": {"created": "2023-01-01", "version": "1.0"}},
        {"config": {"debug": False, "timeout": 5000}},
    ]


@pytest.fixture
def list_values() -> list[list[Any]]:
    """List cache values."""
    return [
        [1, 2, 3, 4, 5],
        ["apple", "banana", "cherry"],
        [{"id": 1}, {"id": 2}, {"id": 3}],
        [True, False, None, "mixed"],
        [],
    ]


@pytest.fixture
def mixed_values() -> list[Any]:
    """Mixed type cache values."""
    return [
        "string_value",
        42,
        3.14,
        True,
        None,
        {"key": "value"},
        [1, 2, {"nested": "dict"}],
        {"list": [1, 2, 3], "dict": {"nested": True}},
    ]


# Error Scenario Fixtures


@pytest.fixture
def cache_error_scenarios() -> list[dict[str, Any]]:
    """Cache error testing scenarios."""
    return [
        {
            "name": "backend_connection_error",
            "error_type": "connection",
            "expected_error": ConnectionError,
        },
        {
            "name": "backend_timeout_error",
            "error_type": "timeout",
            "expected_error": TimeoutError,
        },
        {
            "name": "invalid_key_error",
            "error_type": "invalid_key",
            "expected_error": ValueError,
        },
        {
            "name": "serialization_error",
            "error_type": "serialization",
            "expected_error": TypeError,
        },
    ]


@pytest.fixture
def backend_failure_scenarios() -> list[dict[str, Any]]:
    """Backend failure testing scenarios."""
    return [
        {
            "name": "redis_connection_failure",
            "backend": "redis",
            "failure_mode": "connection_refused",
            "expected_error": ConnectionError,
        },
        {
            "name": "memcached_unavailable",
            "backend": "memcached",
            "failure_mode": "server_unavailable",
            "expected_error": ConnectionError,
        },
        {
            "name": "memory_backend_full",
            "backend": "memory",
            "failure_mode": "out_of_memory",
            "expected_error": MemoryError,
        },
    ]


# Setup/Teardown Fixtures


if pytest_asyncio is None:

    @pytest.fixture(autouse=True)
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

else:

    @pytest_asyncio.fixture(autouse=True, scope="function")
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

    @pytest_asyncio.fixture
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

    @pytest_asyncio.fixture
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

        # Could log final metrics here if needed
        # metrics = await cache_client.get_cache_metrics()
        # print(f"Final cache metrics: {metrics}")

else:

    @pytest_asyncio.fixture
    async def cache_metrics_collector(
        cache_client: CacheTestClient,
    ) -> AsyncGenerator[CacheTestClient, None]:
        """Cache client with metrics collection."""
        # Reset metrics at start
        await cache_client.reset_cache_metrics()

        yield cache_client

        # Could log final metrics here if needed
        # metrics = await cache_client.get_cache_metrics()
        # print(f"Final cache metrics: {metrics}")


# Performance Testing Fixtures


@pytest.fixture
def performance_test_data() -> dict[str, Any]:
    """Data for performance testing."""
    return {
        "small_payloads": [(f"key_{i}", f"value_{i}") for i in range(100)],
        "medium_payloads": [(f"key_{i}", {"data": "x" * 1000}) for i in range(50)],
        "large_payloads": [(f"key_{i}", {"data": "x" * 10000}) for i in range(10)],
    }


@pytest.fixture
def concurrent_test_keys() -> list[str]:
    """Keys for concurrent access testing."""
    return [f"concurrent_key_{i}" for i in range(20)]


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

    @_async_fixture
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
