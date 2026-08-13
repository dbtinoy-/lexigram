"""GraphQL module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.graphql.protocols import GraphQLExecutorProtocol
from lexigram.di.module import DynamicModule, Module, module


@module()
class GraphQLModule(Module):
    """GraphQL layer (Strawberry): schema building, execution, federation, and subscriptions.

    Call :meth:`configure` to configure and mount the GraphQL endpoint.

    Usage::

        import strawberry

        @strawberry.type
        class Query:
            @strawberry.field
            def hello(self) -> str:
                return "world"

        @module(
            imports=[GraphQLModule.configure(query_class=Query)]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: Any | None = None,
        query_class: Any | None = None,
        mutation_class: Any | None = None,
        subscription_class: Any | None = None,
        context_factory_class: Any | None = None,
    ) -> DynamicModule:
        """Create a GraphQLModule with explicit configuration.

        Args:
            config: :class:`~lexigram.graphql.config.GraphQLConfig` or ``None``
                for framework defaults.
            query_class: Optional root Strawberry ``Query`` type.
            mutation_class: Optional root Strawberry ``Mutation`` type.
            subscription_class: Optional root Strawberry ``Subscription`` type.
            context_factory_class: Optional custom :class:`~lexigram.graphql.core.context.ContextFactory`
                subclass. When ``None``, the framework's default ``ContextFactory`` is used.
                Subclasses can override ``create_context()`` to attach application-specific
                services to the GraphQL context.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.graphql.di.provider import GraphQLProvider

        return DynamicModule(
            module=cls,
            providers=[
                GraphQLProvider(
                    config=config,
                    query_class=query_class,
                    mutation_class=mutation_class,
                    subscription_class=subscription_class,
                    context_factory_class=context_factory_class,
                )
            ],
            exports=[GraphQLExecutorProtocol],
            is_global=True,
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op GraphQLModule suitable for unit testing.

        Registers a GraphQLProvider with no schema types configured.
        Useful for testing application structure without a real GraphQL
        executor.

        Returns:
            A DynamicModule with noop GraphQL configuration.
        """
        from lexigram.graphql.di.provider import GraphQLProvider

        return DynamicModule(
            module=cls,
            providers=[GraphQLProvider()],
            exports=[GraphQLExecutorProtocol],
            is_global=True,
        )


__all__ = ["GraphQLModule"]
