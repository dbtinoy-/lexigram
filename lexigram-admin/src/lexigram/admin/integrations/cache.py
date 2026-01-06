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
    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None

    async def get_or_set(
        self, key: str, factory: Callable[[], Awaitable[Any]], ttl: int | None = None
    ) -> Any:
        return await factory()


class CacheIntegration:
    """Adapter that decorates data-source calls with a cache layer.

    Gracefully no-ops when ``lexigram-cache`` is not installed or when the
    integration is disabled via config.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._cache: Any = None
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
        effective_ttl = ttl or getattr(self._config, "default_ttl_seconds", 60)
        return await self._cache.get_or_set(key, factory, effective_ttl)

    async def invalidate(self, resource_name: str) -> None:
        if hasattr(self._cache, "delete_pattern"):
            await self._cache.delete_pattern(
                getattr(self._config, "key_prefix", "admin") + f":{resource_name}:*"
            )


__all__ = ["CacheIntegration", "CacheableSpec"]
