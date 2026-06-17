"""NoSQL document store module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.nosql.nosql import DocumentStoreProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.nosql.config import NoSQLConfig


@module()
class NoSQLModule(Module):
    """Document store integration (MongoDB, and future drivers).

    Registers :class:`~lexigram.contracts.data.nosql.nosql.DocumentStoreProtocol`
    for constructor injection.

    Call :meth:`configure` to configure and register the document-store backend,
    or :meth:`stub` for an isolated setup with no external service
    dependencies.

    Usage::

        from lexigram.nosql.config import NoSQLConfig

        @module(
            imports=[NoSQLModule.configure(NoSQLConfig(driver="mongodb"))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: NoSQLConfig | Any | None = None,
        enable_ttl: bool = True,
    ) -> DynamicModule:
        """Create a NoSQLModule with explicit configuration.

        Args:
            config: :class:`~lexigram.nosql.config.NoSQLConfig` or ``None``
                to use defaults (reads from environment variables).
            enable_ttl: Enable TTL (time-to-live) index support for documents.
                Defaults to ``True``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.nosql.di.provider import NoSQLProvider

        return DynamicModule(
            module=cls,
            providers=[NoSQLProvider(config=config)],
            exports=[DocumentStoreProtocol],
        )

    @classmethod
    def scope(cls, *repositories: type, **kwargs: Any) -> DynamicModule:
        """Scope document repository classes into a feature module.

        Registers the given repository classes as providers and exports them
        for constructor injection within the feature.  The parent module graph
        must already include :meth:`NoSQLModule.configure` — this does
        **not** create a new document store connection.

        Uses the anonymous token pattern so both ``configure()`` and
        ``scope()`` can coexist in the same compiled graph without a
        ``ModuleDuplicateError``.

        Example::

            @module(
                imports=[
                    NoSQLModule.configure(config),
                    NoSQLModule.scope(ProductRepository, CategoryRepository),
                ]
            )
            class CatalogFeatureModule(Module):
                pass

        Args:
            *repositories: Document repository classes to register and export.
            **kwargs: Additional DynamicModule fields (exports, imports, etc.).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` scoped to this feature.
        """
        token = type(
            f"_{cls.__name__}Scope",
            (cls,),
            {"__lexigram_scope_of__": cls},
        )
        return DynamicModule(
            module=token,
            providers=list(repositories),
            exports=list(kwargs.get("exports", list(repositories))),
        )

    @classmethod
    def stub(cls, config: NoSQLConfig | None = None) -> DynamicModule:
        """Create a NoSQLModule suitable for unit and integration testing.

        Uses a minimal ``NoSQLConfig`` with the MongoDB driver.  A
        reachable MongoDB instance is still required at boot — this
        package ships no in-memory backend.  Point ``config`` at a test
        MongoDB (``MongoDBConfig(uri=..., database=...)``) when the
        defaults are unsuitable.

        Args:
            config: Optional :class:`~lexigram.nosql.config.NoSQLConfig` override.
                Uses safe defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.nosql.di.provider import NoSQLProvider

        return DynamicModule(
            module=cls,
            providers=[NoSQLProvider(config=config)],
            exports=[DocumentStoreProtocol],
        )


__all__ = ["NoSQLModule"]
