"""Cache data, key, value, TTL, and backend fixtures.

Provides sample payloads, key sets, TTL values, and backend instances for
cache testing scenarios.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.testing.clients.cache.data import CacheTestData

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
