"""Cache integration — wraps Resource.cacheable with a caching layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


@dataclass(frozen=True)
class CacheableSpec:
    ttl_seconds: int | None = None
    key_template: str | None = None
    invalidate_on_actions: tuple[str, ...] = ()


class _NoOpCache:
    """Small cache-shaped fallback used when the optional package is absent."""

    async def get(self, key: str) -> None:  # noqa: ARG002
        return None

    async def set(
        self, key: str, value: Any, ttl: int | None = None  # noqa: ARG002
    ) -> None:
        return None

    async def delete(self, key: str) -> None:  # noqa: ARG002
        return None


class CacheIntegration:
    """Adapter that decorates data-source calls with a cache layer.

    Gracefully no-ops when ``lexigram-cache`` is not installed or when the
    integration is disabled via config.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        # Keep the adapter callable before DI boot as well as after it. This
        # makes optional integrations safe for tests and early lifecycle hooks.
        self._cache: Any = _NoOpCache()
        self._enabled = False

    def register(self, container: ContainerRegistrarProtocol) -> None:
        from lexigram.admin.config import CacheIntegrationConfig
        from lexigram.admin.integrations._optional import is_installed

        cfg = self._config
        if not isinstance(cfg, CacheIntegrationConfig):
            cfg = CacheIntegrationConfig()
        if not cfg.enabled:
            self._cache = _NoOpCache()
            return
        if not is_installed("lexigram.cache"):
            self._cache = _NoOpCache()
            return
        self._enabled = True
        # Resolution deferred to boot()

    async def boot(self, container: ContainerResolverProtocol) -> None:
        if not self._enabled:
            return
        try:
            from lexigram.contracts.infra.cache import CacheBackendProtocol

            self._cache = await container.resolve(CacheBackendProtocol)
        except Exception:  # noqa: BLE001
            self._cache = _NoOpCache()

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if not isinstance(self._cache, _NoOpCache) else "noop"
        }

    def cache_key(self, resource_name: str, *parts: str) -> str:
        prefix = getattr(self._config, "key_prefix", "admin")
        return f"{prefix}:{resource_name}:" + ":".join(parts)

    async def get_or_compute(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: int | None = None,
    ) -> Any:
        """Read through the contract cache.

        Populates misses atomically enough for callers.

        ``CacheBackendProtocol`` intentionally exposes primitive get/set
        operations, not a convenience ``get_or_set`` method.  The previous
        adapter called that non-contract method, so enabling the real cache
        package made every cached list query fail.  Keep the orchestration in
        the admin adapter and accept both plain values and ``Result`` returns
        from backend implementations.
        """
        try:
            cached = await self._cache.get(key)
            cached, cache_read_ok = self._unwrap_result(cached)
        except Exception:  # noqa: BLE001 — cache is an optional optimization
            cached, cache_read_ok = None, False
        if cache_read_ok and cached is not None:
            return cached

        value = await factory()
        try:
            stored = await self._cache.set(
                key,
                value,
                ttl or getattr(self._config, "default_ttl_seconds", 60),
            )
            # A failed cache write must not turn a successful resource query
            # into an admin error. The computed value is still valid here.
            self._unwrap_result(stored)
        except Exception:  # noqa: BLE001 — cache is an optional optimization
            pass
        return value

    @staticmethod
    def _unwrap_result(value: Any) -> tuple[Any, bool]:
        """Return ``(payload, succeeded)`` for plain values or Result objects."""
        if hasattr(value, "is_ok") and callable(value.is_ok):
            if not value.is_ok():
                return None, False
            return value.unwrap(), True
        return value, True

    async def invalidate(self, resource_name: str) -> None:
        if hasattr(self._cache, "delete_pattern"):
            await self._cache.delete_pattern(
                getattr(self._config, "key_prefix", "admin") + f":{resource_name}:*"
            )


__all__ = ["CacheIntegration", "CacheableSpec"]
