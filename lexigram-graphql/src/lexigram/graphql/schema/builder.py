"""GraphQL schema builder.

This module provides utilities for building GraphQL schemas
from types, queries, mutations, and subscriptions.
"""

from __future__ import annotations

from typing import Any

import strawberry
from strawberry import Schema

from lexigram.graphql.config import GraphQLConfig
from lexigram.logging import get_logger

logger = get_logger(__name__)


class SchemaBuilderProtocol:
    """Build GraphQL schemas with configuration.

    Provides a fluent interface for constructing GraphQL schemas
    with proper configuration, extensions, and type registration.

    Example:
        ```python
        builder = SchemaBuilderProtocol()

        schema = (
            builder
            .query(Query)
            .mutation(Mutation)
            .subscription(Subscription)
            .add_extension(QueryLogger())
            .build()
        )
        ```
    """

    def __init__(
        self,
        config: GraphQLConfig | None = None,
    ) -> None:
        """Initialize the schema builder.

        Args:
            config: GraphQL configuration.
        """
        self._config = config or GraphQLConfig()
        self._query_type: type[Any] | None = None
        self._mutation_type: type[Any] | None = None
        self._subscription_type: type[Any] | None = None
        self._types: list[type[Any]] = []
        # Keep extensions loosely typed to avoid coupling to strawberry's
        # concrete Extension type which can vary between versions.
        self._extensions: list[Any] = []
        self._directives: list[Any] = []
        self._scalar_overrides: dict[Any, Any] = {}
        self._dataloader_factories: dict[str, Any] = {}

    def query(self, query_type: type[Any]) -> SchemaBuilderProtocol:
        """Set the query type.

        Args:
            query_type: The query type class.

        Returns:
            Self for chaining.
        """
        self._query_type = query_type
        return self

    def mutation(self, mutation_type: type[Any]) -> SchemaBuilderProtocol:
        """Set the mutation type.

        Args:
            mutation_type: The mutation type class.

        Returns:
            Self for chaining.
        """
        self._mutation_type = mutation_type
        return self

    def subscription(self, subscription_type: type[Any]) -> SchemaBuilderProtocol:
        """Set the subscription type.

        Args:
            subscription_type: The subscription type class.

        Returns:
            Self for chaining.
        """
        self._subscription_type = subscription_type
        return self

    def add_type(self, type_class: type[Any]) -> SchemaBuilderProtocol:
        """Add an additional type to the schema.

        Args:
            type_class: The type class to add.

        Returns:
            Self for chaining.
        """
        self._types.append(type_class)
        return self

    def add_types(self, *type_classes: type[Any]) -> SchemaBuilderProtocol:
        """Add multiple types to the schema.

        Args:
            type_classes: Type classes to add.

        Returns:
            Self for chaining.
        """
        self._types.extend(type_classes)
        return self

    def add_extension(self, extension: Any) -> SchemaBuilderProtocol:
        """Add a schema extension.

        Args:
            extension: The extension to add (kept as Any to avoid strict coupling
                       to Strawberry's extension type in various environments).

        Returns:
            Self for chaining.
        """
        self._extensions.append(extension)
        return self

    def add_dataloader(self, name: str, factory: Any) -> SchemaBuilderProtocol:
        """Register a DataLoaderProtocol factory for per-request loader initialisation.

        Stored factories are wired into :class:`ContextFactory` by
        :class:`~lexigram.graphql.providers.GraphQLProvider` during ``boot()``,
        so loaders are available inside resolvers via
        ``context.get_dataloader(name)``.

        Args:
            name: Unique loader name.
            factory: Callable ``(context) -> DataLoaderProtocol`` invoked per-request.

        Returns:
            Self for chaining.
        """
        self._dataloader_factories[name] = factory
        return self

    def add_directive(self, directive: Any) -> SchemaBuilderProtocol:
        """Add a custom directive.

        Args:
            directive: The directive to add.

        Returns:
            Self for chaining.
        """
        self._directives.append(directive)
        return self

    def scalar_override(
        self,
        original: Any,
        override: Any,
    ) -> SchemaBuilderProtocol:
        """Override a scalar type.

        Args:
            original: Original scalar type.
            override: Override scalar type.

        Returns:
            Self for chaining.
        """
        self._scalar_overrides[original] = override
        return self

    def build(self) -> Schema:
        """Build the GraphQL schema.

        Returns:
            Configured Strawberry schema.

        Raises:
            ValueError: If no query type is set and no default is provided.
        """

        if self._query_type is None:

            @strawberry.type
            class EmptyQuery:
                @strawberry.field
                def health(self) -> str:
                    return "ok"

            self._query_type = EmptyQuery
            logger.info("No query type provided, initialized with default EmptyQuery")

        # Build schema kwargs
        schema_kwargs: dict[str, Any] = {
            "query": self._query_type,
        }

        if self._mutation_type:
            schema_kwargs["mutation"] = self._mutation_type

        if self._subscription_type:
            schema_kwargs["subscription"] = self._subscription_type

        if self._types:
            schema_kwargs["types"] = self._types

        if self._extensions:
            schema_kwargs["extensions"] = self._extensions

        if self._directives:
            schema_kwargs["directives"] = self._directives

        if self._scalar_overrides:
            schema_kwargs["scalar_overrides"] = self._scalar_overrides

        from lexigram.graphql.security.alias import AliasLimitExtension
        from lexigram.graphql.security.complexity import ComplexityLimitExtension
        from lexigram.graphql.security.depth import DepthLimitExtension

        cfg = self._config
        security_extensions: list[Any] = []
        if cfg.depth_limit.enabled:
            security_extensions.append(
                DepthLimitExtension(
                    max_depth=cfg.depth_limit.max_depth,
                    ignore_introspection=cfg.depth_limit.ignore_introspection,
                )
            )
        if cfg.complexity.enabled:
            security_extensions.append(
                ComplexityLimitExtension(
                    max_complexity=cfg.complexity.max_complexity,
                    default_field_cost=cfg.complexity.default_field_cost,
                    default_list_cost=cfg.complexity.default_list_cost,
                )
            )
        if cfg.alias_limit.enabled:
            security_extensions.append(
                AliasLimitExtension(max_aliases=cfg.alias_limit.max_aliases)
            )

        if security_extensions:
            schema_kwargs["extensions"] = [
                *security_extensions,
                *self._extensions,
            ]

        # Create schema
        schema = Schema(**schema_kwargs)

        logger.info(
            "Built GraphQL schema with query=%s, mutation=%s, subscription=%s",
            self._query_type.__name__,
            self._mutation_type.__name__ if self._mutation_type else None,
            self._subscription_type.__name__ if self._subscription_type else None,
        )

        return schema

    @property
    def config(self) -> GraphQLConfig:
        """Get the configuration."""
        return self._config


def create_schema(
    query: type[Any],
    mutation: type[Any] | None = None,
    subscription: type[Any] | None = None,
    types: list[type[Any]] | None = None,
    extensions: list[Any] | None = None,
    config: GraphQLConfig | None = None,
) -> Schema:
    """Create a GraphQL schema (convenience function).

    Args:
        query: Query type class.
        mutation: Optional mutation type class.
        subscription: Optional subscription type class.
        types: Additional type classes.
        extensions: Schema extensions.
        config: GraphQL configuration.

    Returns:
        Configured Strawberry schema.

    Example:
        ```python
        schema = create_schema(
            query=Query,
            mutation=Mutation,
            config=GraphQLConfig(depth_limit=5),
        )
        ```
    """
    builder = SchemaBuilderProtocol(config=config)
    builder.query(query)

    if mutation:
        builder.mutation(mutation)

    if subscription:
        builder.subscription(subscription)

    if types:
        builder.add_types(*types)

    if extensions:
        for ext in extensions:
            builder.add_extension(ext)

    return builder.build()


__all__ = ["SchemaBuilderProtocol", "create_schema"]
