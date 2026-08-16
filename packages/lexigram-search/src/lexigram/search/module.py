"""Search engine module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.search import SearchEngineProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.search.config import SearchConfig


@module()
class SearchModule(Module):
    """Full-text and semantic search engine integration (Meilisearch, SQLite, Postgres).

    Registers :class:`~lexigram.contracts.search.SearchEngineProtocol` for
    constructor injection.

    Call :meth:`configure` to configure the search backend, or :meth:`stub`
    for an isolated in-memory setup with no external service dependencies.

    Usage::

        from lexigram.search.config import SearchConfig

        @module(
            imports=[SearchModule.configure(SearchConfig(backend="meilisearch"))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: SearchConfig | Any | None = None,
        enable_facets: bool = True,
    ) -> DynamicModule:
        """Create a SearchModule with explicit configuration.

        Args:
            config: :class:`~lexigram.search.config.SearchConfig` or a
                pre-built :class:`~lexigram.search.engine.SearchEngine` instance.
                Passing ``None`` raises ``ValueError`` — a backend must be
                specified explicitly.
            enable_facets: Enable faceted search / filterable attributes on
                the backing index.  Defaults to ``True``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.

        Raises:
            ValueError: If *config* is ``None``.
        """
        if config is None:
            raise ValueError(
                "SearchModule.configure() requires a SearchConfig or SearchEngine instance."
            )

        from lexigram.search.di.provider import SearchProvider
        from lexigram.search.engine import SearchEngine

        if isinstance(config, SearchEngine):
            provider = SearchProvider(backend=config)
        else:
            provider = SearchProvider.configure(config)

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[SearchEngineProtocol],
        )

    @classmethod
    def stub(cls, config: SearchConfig | None = None) -> DynamicModule:
        """Create a SearchModule suitable for unit and integration testing.

        Uses an in-memory (null) backend with no external service dependencies.

        Args:
            config: Optional :class:`~lexigram.search.config.SearchConfig`
                override.  Uses an in-memory backend when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.search.di.provider import SearchProvider

        if config is not None:
            provider = SearchProvider.configure(config)
        else:
            provider = SearchProvider.with_memory()

        return DynamicModule(
            module=cls,
            providers=[provider],
            exports=[SearchEngineProtocol],
        )


__all__ = ["SearchModule"]
