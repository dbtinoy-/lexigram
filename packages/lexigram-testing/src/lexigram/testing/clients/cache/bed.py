"""
Testing bed: `CacheTestBed`.

Split out from `client.py` to keep responsibilities separated.
"""

from __future__ import annotations

from typing import Any, Self

from lexigram.cache import CacheProvider, CacheService, MemoryCacheBackend
from lexigram.cache.config import default_cache_config
from lexigram.logging import get_logger
from lexigram.testing import TestEnvironment
from lexigram.testing.clients.cache.data import CacheTestData


class CacheTestBed(TestEnvironment):
    """Test bed for lexigram-cache testing.

    Provides a complete testing environment with cache providers,
    backends, and services.
    """

    def __init__(self, backend_type: str = "memory", **kwargs: Any) -> None:
        """Initialize the cache test bed."""
        super().__init__(**kwargs)
        self.backend_type = backend_type
        self._cache_provider: CacheProvider | None = None
        self._cache_service: CacheService | None = None

    async def setup(self) -> Any:
        app = await super().setup()
        await self.setup_cache_providers()
        return app

    async def setup_cache_providers(self) -> None:
        cache_config = default_cache_config()
        backend = MemoryCacheBackend(config=cache_config)

        self._cache_provider = CacheProvider()
        self._cache_provider._backends["memory"] = backend
        self._cache_provider._services["memory"] = CacheService(
            provider=self._cache_provider,
        )

        original_get_backend = self._cache_provider.get_backend
        provider = self._cache_provider
        assert provider is not None

        def get_backend_with_default(backend_name: str | None = None) -> Any:
            if backend_name is None:
                return provider._backends["memory"]
            return original_get_backend(backend_name)

        self._cache_provider.get_backend = get_backend_with_default  # type: ignore[method-assign]

        assert self._cache_provider is not None
        if self.container is not None:
            provider = self._cache_provider
            self.container.singleton(CacheProvider, lambda: provider)

        assert self._cache_provider is not None
        self._cache_service = self._cache_provider._services["memory"]
        if self.container is not None:
            provider_service = self._cache_service
            self.container.singleton(CacheService, lambda: provider_service)

    async def teardown_cache_providers(self) -> None:
        if self._cache_service:
            try:
                await self._cache_service.clear()
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
                    "Cache cleanup error (ignored): %s",
                    e,
                )

        await super().teardown_providers()  # type: ignore[misc]

    @property
    def cache_provider(self) -> CacheProvider:
        assert self._cache_provider is not None
        return self._cache_provider

    @property
    def cache_service(self) -> CacheService:
        if self._cache_service is None:
            raise RuntimeError("Test bed has not been configured with a cache service")
        return self._cache_service

    def create_test_data(self, key_prefix: str = "test") -> CacheTestData:
        return CacheTestData(key_prefix)

    async def __aenter__(self) -> Self:
        await self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.teardown()  # type: ignore[misc,func-returns-value]
