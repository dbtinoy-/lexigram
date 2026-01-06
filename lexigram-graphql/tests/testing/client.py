"""GraphQL test client.

This module provides a test client for executing GraphQL
queries in tests without HTTP overhead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from strawberry import Schema as StrawberrySchema

    Schema = StrawberrySchema
else:
    from strawberry import Schema

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class TestResult(Generic[T]):
    """Result from a test query execution.

    Attributes:
        data: Response data.
        errors: List of errors.
        extensions: Response extensions.
        raw_response: Raw response object.
    """

    data: T | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    raw_response: Any = None

    @property
    def has_errors(self) -> bool:
        """Check if result has errors."""
        return len(self.errors) > 0

    @property
    def is_successful(self) -> bool:
        """Check if result is successful (no errors)."""
        return not self.has_errors

    @property
    def first_error(self) -> dict[str, Any] | None:
        """Get the first error if any."""
        if self.errors:
            return self.errors[0]
        return None

    @property
    def error_messages(self) -> list[str]:
        """Get all error messages."""
        return [e.get("message", str(e)) for e in self.errors]


class GraphQLTestClient:
    """Test client for GraphQL schemas.

    Executes queries directly against a schema without
    HTTP overhead, making tests fast and reliable.

    Example:
        ```python
        from lexigram.graphql.tests.testing import GraphQLTestClient

        schema = strawberry.Schema(query=Query)
        client = GraphQLTestClient(schema)

        # Execute a query
        result = await client.query('''
            query {
                user(id: "1") {
                    name
                }
            }
        ''')

        assert result.is_successful
        assert result.data["user"]["name"] == "John"
        ```
    """

    def __init__(
        self,
        schema: Schema,
        default_context: Any = None,
    ) -> None:
        """Initialize the test client.

        Args:
            schema: Strawberry GraphQL schema.
            default_context: Default context for all queries.
        """
        self._schema = schema
        self._default_context = default_context

    @property
    def schema(self) -> Schema:
        """Get the schema."""
        return self._schema

    async def query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any = None,
    ) -> TestResult[Any]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Query variables.
            operation_name: Operation name to execute.
            context: Context for this query.

        Returns:
            Test result with data and errors.
        """
        return await self.execute(
            query=query,
            variables=variables,
            operation_name=operation_name,
            context=context,
        )

    async def mutation(
        self,
        mutation: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any = None,
    ) -> TestResult[Any]:
        """Execute a GraphQL mutation.

        Args:
            mutation: GraphQL mutation string.
            variables: Mutation variables.
            operation_name: Operation name to execute.
            context: Context for this mutation.

        Returns:
            Test result with data and errors.
        """
        return await self.execute(
            query=mutation,
            variables=variables,
            operation_name=operation_name,
            context=context,
        )

    async def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context: Any = None,
    ) -> TestResult[Any]:
        """Execute a GraphQL operation.

        Args:
            query: GraphQL query/mutation string.
            variables: Operation variables.
            operation_name: Operation name to execute.
            context: Context for this operation.

        Returns:
            Test result with data and errors.
        """
        ctx = context or self._default_context

        result = await self._schema.execute(
            query=query,
            variable_values=variables,
            operation_name=operation_name,
            context_value=ctx,
        )

        test_result: TestResult[Any] = TestResult(
            data=result.data,
            extensions=result.extensions or {},
            raw_response=result,
        )

        if result.errors:
            for error in result.errors:
                test_result.errors.append(
                    {
                        "message": error.message,
                        "locations": (
                            [
                                {"line": loc.line, "column": loc.column}
                                for loc in error.locations
                            ]
                            if error.locations
                            else None
                        ),
                        "path": list(error.path) if error.path else None,
                        "extensions": error.extensions or {},
                    },
                )

        return test_result

    async def introspect(self) -> TestResult[Any]:
        """Execute an introspection query.

        Returns:
            Test result with schema information.
        """
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                }
                queryType {
                    name
                }
                mutationType {
                    name
                }
            }
        }
        """
        return await self.query(introspection_query)

    def with_context(
        self,
        context: Any,
    ) -> GraphQLTestClient:
        """Create a new client with the given context.

        Args:
            context: Context to use.

        Returns:
            New client with context.
        """
        return GraphQLTestClient(
            schema=self._schema,
            default_context=context,
        )

    def with_user(
        self,
        user: Any,
    ) -> GraphQLTestClient:
        """Create a new client with the given user.

        Args:
            user: User to set in context.

        Returns:
            New client with user context.
        """
        context = {"user": user}
        return self.with_context(context)


__all__ = ["GraphQLTestClient", "TestResult"]
