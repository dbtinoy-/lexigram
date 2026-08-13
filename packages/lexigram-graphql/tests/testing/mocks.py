"""GraphQL testing mocks and utilities.

This module provides mock implementations for testing GraphQL applications.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class MockDataLoader(Generic[K, V]):
    """DataLoaderProtocol with predefined responses for testing.

    Example:
        ```python
        user_loader = MockDataLoader[str, User]({
            "1": User(id="1", name="Alice"),
            "2": User(id="2", name="Bob"),
        })

        # In resolver
        user = await user_loader.load("1")
        ```
    """

    def __init__(self, data: dict[K, V]):
        """Initialize the mock DataLoaderProtocol.

        Args:
            data: Dictionary mapping keys to values.
        """
        self._data = data

    async def load(self, key: K) -> V | None:
        """Load a value by key.

        Args:
            key: The key to load.

        Returns:
            The value if found, None otherwise.
        """
        return self._data.get(key)

    async def load_many(self, keys: list[K]) -> list[V | None]:
        """Load multiple values by keys.

        Args:
            keys: List of keys to load.

        Returns:
            List of values (or None for missing keys).
        """
        return [self._data.get(k) for k in keys]


class ContextBuilder:
    """Fluent builder for test GraphQLContext.

    Example:
        ```python
        context = (ContextBuilder()
            .with_user(user)
            .with_loader("users", user_loader)
            .with_request_id("test-123")
            .build())
        ```
    """

    def __init__(self):
        """Initialize the context builder."""
        self._user: Any = None
        self._loaders: dict[str, Any] = {}
        self._request_id: str | None = None
        self._metadata: dict[str, Any] = {}
        self._headers: dict[str, str] = {}

    def with_user(self, user: Any) -> ContextBuilder:
        """Add a user to the context.

        Args:
            user: The user object.

        Returns:
            Self for chaining.
        """
        self._user = user
        return self

    def with_loader(self, name: str, loader: Any) -> ContextBuilder:
        """Add a DataLoaderProtocol to the context.

        Args:
            name: Name of the loader.
            loader: The DataLoaderProtocol instance.

        Returns:
            Self for chaining.
        """
        self._loaders[name] = loader
        return self

    def with_request_id(self, request_id: str) -> ContextBuilder:
        """Add a request ID to the context.

        Args:
            request_id: The request ID.

        Returns:
            Self for chaining.
        """
        self._request_id = request_id
        return self

    def with_metadata(self, **kwargs: Any) -> ContextBuilder:
        """Add metadata to the context.

        Args:
            **kwargs: Metadata key-value pairs.

        Returns:
            Self for chaining.
        """
        self._metadata.update(kwargs)
        return self

    def with_header(self, name: str, value: str) -> ContextBuilder:
        """Add a header to the context.

        Args:
            name: Header name.
            value: Header value.

        Returns:
            Self for chaining.
        """
        self._headers[name] = value
        return self

    def build(self) -> dict[str, Any]:
        """Build the context dictionary.

        Returns:
            Context dictionary.
        """
        return {
            "user": self._user,
            "request_id": self._request_id,
            "loaders": self._loaders,
            "metadata": self._metadata,
            "headers": self._headers,
        }


@dataclass
class MockExecutionResult:
    """Mock execution result for testing.

    Attributes:
        data: Response data.
        errors: List of errors.
        extensions: Response extensions.
    """

    data: dict | None = None
    errors: list[dict] = field(default_factory=list)
    extensions: dict = field(default_factory=dict)


def create_mock_resolver(
    return_value: Any,
) -> Callable[..., Any]:
    """Create a mock resolver that returns a predefined value.

    Args:
        return_value: The value to return.

    Returns:
        Mock resolver function.
    """

    async def resolver(*args, **kwargs):
        # Simulate async resolver
        return return_value

    return resolver


def create_mock_field(
    name: str,
    type_: str,
    resolver: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Create a mock GraphQL field definition.

    Args:
        name: Field name.
        type_: GraphQL type string.
        resolver: Optional resolver function.

    Returns:
        Field definition dictionary.
    """
    return {
        "name": name,
        "type": type_,
        "resolver": resolver,
    }


class MockSchemaBuilder:
    """Builder for creating test Strawberry schemas.

    Delegates to the real :class:`~lexigram.graphql.schema.builder.SchemaBuilderProtocol`
    so that ``build()`` always returns a valid :class:`strawberry.Schema` instance
    rather than a plain ``dict``.

    Example:
        ```python
        @strawberry.type
        class TestQuery:
            @strawberry.field
            def hello(self) -> str:
                return "world"

        schema = (MockSchemaBuilder()
            .query(TestQuery)
            .build())
        ```
    """

    def __init__(self) -> None:
        """Initialize the schema builder."""
        from lexigram.graphql.schema.builder import SchemaBuilderProtocol

        self._builder = SchemaBuilderProtocol()

    def query(self, query_type: type) -> MockSchemaBuilder:
        """Set the query type.

        Args:
            query_type: A Strawberry-decorated query class.

        Returns:
            Self for chaining.
        """
        self._builder.query(query_type)
        return self

    def mutation(self, mutation_type: type) -> MockSchemaBuilder:
        """Set the mutation type.

        Args:
            mutation_type: A Strawberry-decorated mutation class.

        Returns:
            Self for chaining.
        """
        self._builder.mutation(mutation_type)
        return self

    def subscription(self, subscription_type: type) -> MockSchemaBuilder:
        """Set the subscription type.

        Args:
            subscription_type: A Strawberry-decorated subscription class.

        Returns:
            Self for chaining.
        """
        self._builder.subscription(subscription_type)
        return self

    def build(self) -> Any:
        """Build and return a real Strawberry schema.

        Returns:
            A configured :class:`strawberry.Schema` instance.
        """
        return self._builder.build()


__all__ = [
    "ContextBuilder",
    "MockDataLoader",
    "MockExecutionResult",
    "MockSchemaBuilder",
    "create_mock_field",
    "create_mock_resolver",
]
