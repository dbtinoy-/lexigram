"""Unit tests for GraphQL schema builder."""

import pytest
from unittest.mock import MagicMock
import strawberry
from lexigram.graphql.schema.builder import SchemaBuilderProtocol, create_schema
from lexigram.graphql.config import GraphQLConfig

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "world"

@strawberry.type
class Mutation:
    @strawberry.mutation
    def do_something(self) -> str:
        return "done"

class TestSchemaBuilder:
    """Test SchemaBuilderProtocol functionality."""

    def test_build_simple(self):
        """Test building simple schema."""
        builder = SchemaBuilderProtocol()
        schema = (
            builder
            .query(Query)
            .build()
        )
        
        assert isinstance(schema, strawberry.Schema)
        # Check query field exists using introspection or similar if possible, 
        # or simplified check:
        assert schema.get_type_by_name("Query") is not None

    def test_build_full(self):
        """Test building full schema with mutation."""
        builder = SchemaBuilderProtocol()
        schema = (
            builder
            .query(Query)
            .mutation(Mutation)
            .build()
        )
        
        assert schema.get_type_by_name("Mutation") is not None

    def test_build_missing_query(self):
        """Test default EmptyQuery when query missing."""
        builder = SchemaBuilderProtocol()
        schema = builder.build()
        
        assert schema.get_type_by_name("EmptyQuery") is not None

    def test_create_schema_helper(self):
        """Test helper function."""
        schema = create_schema(query=Query)
        assert isinstance(schema, strawberry.Schema)

    def test_extensions(self):
        """Test adding extensions."""
        ext = MagicMock()
        builder = SchemaBuilderProtocol()
        schema = (
            builder
            .query(Query)
            .add_extension(ext)
            .build()
        )
        # Strawberry stores extensions in the schema config or similar
        # Depending on version, can inspect schema.extensions
        pass # Just ensure it doesn't crash for now

    def test_full_fluent_chain(self):
        """Full .query().mutation().subscription().add_types().add_extension().add_dataloader().build() chain."""
        @strawberry.type
        class Subscription:
            @strawberry.subscription
            async def on_event(self) -> str:
                yield "event"  # pragma: no cover

        @strawberry.type
        class ExtraType:
            value: str

        loader_factory = MagicMock()
        ext = MagicMock()

        builder = SchemaBuilderProtocol()
        schema = (
            builder
            .query(Query)
            .mutation(Mutation)
            .subscription(Subscription)
            .add_types(ExtraType)
            .add_extension(ext)
            .add_dataloader("users", loader_factory)
            .build()
        )

        assert isinstance(schema, strawberry.Schema)
        # Verify all builder state was accumulated
        assert builder._mutation_type is Mutation
        assert builder._subscription_type is Subscription
        assert ExtraType in builder._types
        assert ext in builder._extensions
        assert builder._dataloader_factories["users"] is loader_factory

    def test_add_dataloader_stores_factory(self):
        """add_dataloader() stores the factory under the given name."""
        factory = MagicMock()
        builder = SchemaBuilderProtocol()
        result = builder.add_dataloader("my_loader", factory)

        assert result is builder  # fluent — returns self
        assert builder._dataloader_factories["my_loader"] is factory

    def test_add_types_returns_self(self):
        """add_types() returns self for chaining."""
        @strawberry.type
        class T:
            x: str

        builder = SchemaBuilderProtocol()
        result = builder.add_types(T)
        assert result is builder
        assert T in builder._types
