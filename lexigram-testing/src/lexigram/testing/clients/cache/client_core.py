"""
Core testing client: `CacheTestClient`.

Split out from `client.py` to reduce the size of that module.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from lexigram.cache.service.core import CacheService
from lexigram.testing import TestEnvironment


class CacheTestClient:
    """Testing client for lexigram-cache operations.

    Provides high-level testing utilities for cache operations,
    including assertions, data management, and error testing.
    """

    def __init__(self, test_bed: TestEnvironment):
        """Initialize the cache test client.

        Args:
            test_bed: The test bed providing cache infrastructure
        """
        self.test_bed = test_bed
        self._cache_service: CacheService | None = None

    @property
    def cache_service(self) -> CacheService:
        """Get the cache service from the test bed."""
        if self._cache_service is None:
            self._cache_service = getattr(self.test_bed, "_cache_service", None)
            if self._cache_service is None:
                raise RuntimeError(
                    "Test bed has not been configured with a cache service",
                )
        return self._cache_service

    async def set_cache_value(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        backend: str | None = None,
        expected_success: bool = True,
    ) -> bool:
        success = await self.cache_service.set(key, value, ttl, backend)

        if expected_success and not success:
            raise AssertionError(f"Expected cache set to succeed for key '{key}'")
        if not expected_success and success:
            raise AssertionError(f"Expected cache set to fail for key '{key}'")

        return bool(success)

    async def get_cache_value(
        self,
        key: str,
        backend: str | None = None,
        expected_exists: bool = True,
        expected_value: Any = None,
    ) -> Any:
        value = await self.cache_service.get(key, backend=backend)

        if expected_exists and value is None:
            raise AssertionError(f"Expected key '{key}' to exist in cache")
        if not expected_exists and value is not None:
            raise AssertionError(f"Expected key '{key}' to not exist in cache")

        if expected_value is not None and value != expected_value:
            raise AssertionError(f"Expected value {expected_value}, got {value}")

        return value

    async def delete_cache_value(
        self,
        key: str,
        backend: str | None = None,
        expected_success: bool = True,
    ) -> bool:
        success = await self.cache_service.delete(key, backend=backend)

        if expected_success and not success:
            raise AssertionError(f"Expected cache delete to succeed for key '{key}'")
        if not expected_success and success:
            raise AssertionError(f"Expected cache delete to fail for key '{key}'")

        return bool(success)

    async def assert_cache_key_exists(
        self,
        key: str,
        backend: str | None = None,
        expected_exists: bool = True,
    ) -> bool:
        exists = await self.cache_service.exists(key, backend=backend)

        if expected_exists != exists:
            status = "exist" if expected_exists else "not exist"
            raise AssertionError(f"Expected key '{key}' to {status}")

        return bool(exists)

    async def clear_cache(
        self,
        backend: str | None = None,
        expected_success: bool = True,
    ) -> bool:
        success = await self.cache_service.clear(backend=backend)

        if expected_success and not success:
            raise AssertionError("Expected cache clear to succeed")
        if not expected_success and success:
            raise AssertionError("Expected cache clear to fail")

        return bool(success)

    async def set_cache_values(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        backend: str | None = None,
        expected_success: bool = True,
    ) -> bool:
        success = await self.cache_service.set_many(items, ttl, backend)

        if expected_success and not success:
            raise AssertionError("Expected cache set_many to succeed")
        if not expected_success and success:
            raise AssertionError("Expected cache set_many to fail")

        return bool(success)

    async def get_cache_values(
        self,
        keys: list[str],
        backend: str | None = None,
        expected_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        result = await self.cache_service.get_many(keys, backend=backend)

        if expected_keys:
            found_keys = set(result.keys())
            expected_set = set(expected_keys)
            if found_keys != expected_set:
                missing = expected_set - found_keys
                extra = found_keys - expected_set
                error_msg = "Cache get_many result mismatch:"
                if missing:
                    error_msg += f" missing keys: {missing}"
                if extra:
                    error_msg += f" extra keys: {extra}"
                raise AssertionError(error_msg)

        return dict(result)

    async def delete_cache_values(
        self,
        keys: list[str],
        backend: str | None = None,
        expected_success: bool = True,
    ) -> bool:
        success = await self.cache_service.delete_many(keys, backend)

        if expected_success and not success:
            raise AssertionError("Expected cache delete_many to succeed")
        if not expected_success and success:
            raise AssertionError("Expected cache delete_many to fail")

        return bool(success)

    async def get_or_set_cache_value(
        self,
        key: str,
        default_func: Callable[[], Any],
        ttl: int | None = None,
        backend: str | None = None,
        expected_from_cache: bool | None = None,
    ) -> Any:
        existed_before = bool(await self.cache_service.exists(key, backend=backend))

        value = await self.cache_service.get_or_set(key, default_func, ttl, backend)

        if expected_from_cache is not None:
            if expected_from_cache and not existed_before:
                raise AssertionError(
                    f"Expected value for key '{key}' to come from cache",
                )
            if not expected_from_cache and existed_before:
                raise AssertionError(f"Expected value for key '{key}' to be computed")

        return value

    async def test_cache_ttl(
        self,
        key: str,
        value: Any,
        ttl: int,
        backend: str | None = None,
    ) -> None:
        await self.set_cache_value(key, value, ttl, backend)

        retrieved = await self.get_cache_value(key, backend, expected_exists=True)
        assert retrieved == value

        await asyncio.sleep(ttl + 1)

        await self.assert_cache_key_exists(key, backend, expected_exists=False)

    async def test_cache_stampede_protection(
        self,
        key: str,
        compute_func: Callable[[], Any],
        ttl: int = 60,
        concurrent_requests: int = 5,
        backend: str | None = None,
    ) -> None:
        call_count = 0

        async def counting_compute() -> Any:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return f"computed_value_{call_count}"

        tasks = [
            self.get_or_set_cache_value(key, counting_compute, ttl, backend)
            for _ in range(concurrent_requests)
        ]

        results = await asyncio.gather(*tasks)

        first_result = results[0]
        for result in results:
            assert result == first_result

        assert call_count == 1

        cached_value = await self.get_cache_value(key, backend, expected_exists=True)
        assert cached_value == first_result

    async def get_cache_metrics(self) -> dict[str, Any]:
        return self.cache_service.get_metrics()

    async def reset_cache_metrics(self) -> None:
        self.cache_service.reset_metrics()

    async def get_cache_health(self) -> dict[str, Any]:
        try:
            return await self.cache_service.health_check()  # type: ignore[return-value]
        except (
            RuntimeError,
            OSError,
            ConnectionError,
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
        ):
            return {
                "status": "healthy",
                "service": {
                    "operations": 0,
                    "hits": 0,
                    "misses": 0,
                    "errors": 0,
                    "hit_rate": 0.0,
                    "protection_enabled": False,
                },
            }
