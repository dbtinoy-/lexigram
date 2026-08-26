"""Cache module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.cache.config import CacheConfig


@module(is_global=True)
class CacheModule(Module):
    """Redis and in-memory cache backends with stampede protection.

    Call :meth:`configure` to register a configured
    :class:`~lexigram.cache.di.provider.CacheProvider` and expose
    :class:`~lexigram.contracts.cache.protocols.CacheBackendProtocol` for injection.

    Usage::

        from lexigram.cache.config import CacheConfig

        @module(
            imports=[CacheModule.configure(CacheConfig(...))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls, config: CacheConfig | dict[str, Any] | None = None
    ) -> DynamicModule:
        """Create a CacheModule with explicit configuration.

        Args:
            config: :class:`~lexigram.cache.config.CacheConfig`, a plain
                ``dict`` of config values, or ``None`` for framework defaults
                (or the orchestrator-injected ``cache`` yaml section).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.cache.admin.contributor import CacheAdminContributor
        from lexigram.cache.config import CacheConfig
        from lexigram.cache.di.provider import CacheProvider
        from lexigram.contracts.ai.llm import SemanticCacheProtocol

        provider = CacheProvider()
        if config is not None:
            if isinstance(config, (dict, CacheConfig)):
                provider.configure(config)
            else:
                raise TypeError(
                    f"config must be CacheConfig or dict, got {type(config).__name__}"
                )

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[
                CacheBackendProtocol,
                SemanticCacheProtocol,
                CacheAdminContributor,
            ],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return an in-memory CacheModule for unit testing.

        Uses an in-memory cache backend with no external Redis connection.
        ``SemanticCacheProtocol`` is not registered (not available without
        embedding client and vector index).

        Returns:
            A DynamicModule backed by in-memory cache storage.
        """
        from lexigram.cache.config import CacheBackendConfig, CacheConfig
        from lexigram.cache.di.provider import CacheProvider
        from lexigram.cache.types import BackendType

        if config is None:
            config = CacheConfig(
                backends=[
                    CacheBackendConfig(
                        name="default",
                        type=BackendType.MEMORY,
                        default=True,
                    )
                ]
            )
        return DynamicModule(
            module=cls,
            providers=[CacheProvider(config=config)],
            exports=[CacheBackendProtocol],
        )


__all__ = ["CacheModule"]
