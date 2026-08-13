"""Tests for GraphQL exceptions."""

import pytest

from lexigram.graphql.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ExecutionError,
    ForbiddenError,
    GraphQLError,
    GraphQLError,
    GraphQLTimeoutError,
    InputGraphQLError,
    ParseError,
    QueryTooComplexError,
    QueryTooDeepError,
    ResolverError,
)
from lexigram.graphql.types import GraphQLErrorCode


class TestGraphQLError:
    """Tests for GraphQLError base class."""

    def test_graphql_exception_instantiation(self) -> None:
        """Should instantiate with message."""
        error = GraphQLError("Test error")
        assert "Test error" in str(error)
        assert error.code == GraphQLErrorCode.INTERNAL_SERVER_ERROR

    def test_graphql_exception_with_code(self) -> None:
        """Should support custom code."""
        error = GraphQLError("Error", code=GraphQLErrorCode.BAD_USER_INPUT)
        assert error.code == GraphQLErrorCode.BAD_USER_INPUT

    def test_graphql_exception_with_extensions(self) -> None:
        """Should support extensions."""
        error = GraphQLError("Error", extra="data")
        assert error.extensions["extra"] == "data"

    def test_graphql_exception_safe_default(self) -> None:
        """Should have safe=False by default."""
        error = GraphQLError("Error")
        assert error.safe is False


class TestGraphQLError:
    """Tests for GraphQLError."""

    def test_graphql_error(self) -> None:
        """Should instantiate."""
        error = GraphQLError("General error")
        assert "General error" in str(error)


class TestExecutionError:
    """Tests for ExecutionError."""

    def test_execution_error(self) -> None:
        """Should instantiate."""
        error = ExecutionError("Execution failed")
        assert "Execution failed" in str(error)


class TestGraphQLTimeoutError:
    """Tests for GraphQLTimeoutError."""

    def test_timeout_error(self) -> None:
        """Should instantiate."""
        error = GraphQLTimeoutError("Request timed out")
        assert "Request timed out" in str(error)


class TestQueryTooDeepError:
    """Tests for QueryTooDeepError."""

    def test_query_too_deep_error(self) -> None:
        """Should instantiate."""
        error = QueryTooDeepError("Query depth exceeded")
        assert "Query depth exceeded" in str(error)
        assert error.code == GraphQLErrorCode.QUERY_TOO_DEEP


class TestInputGraphQLError:
    """Tests for InputGraphQLError."""

    def test_input_error(self) -> None:
        """Should instantiate with safe=True."""
        error = InputGraphQLError("Invalid input")
        assert "Invalid input" in str(error)
        assert error.code == GraphQLErrorCode.BAD_USER_INPUT
        assert error.safe is True


class TestParseError:
    """Tests for ParseError."""

    def test_parse_error(self) -> None:
        """Should instantiate."""
        error = ParseError("Parse failed")
        assert "Parse failed" in str(error)
        assert error.code == GraphQLErrorCode.GRAPHQL_PARSE_FAILED


class TestQueryTooComplexError:
    """Tests for QueryTooComplexError."""

    def test_query_too_complex_error(self) -> None:
        """Should instantiate."""
        error = QueryTooComplexError("Query too complex")
        assert "Query too complex" in str(error)
        assert error.code == GraphQLErrorCode.QUERY_TOO_COMPLEX


class TestResolverError:
    """Tests for ResolverError."""

    def test_resolver_error(self) -> None:
        """Should instantiate."""
        error = ResolverError("ResolverProtocol failed")
        assert "ResolverProtocol failed" in str(error)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_authentication_error(self) -> None:
        """Should instantiate."""
        error = AuthenticationError("Not authenticated")
        assert "Not authenticated" in str(error)
        assert error.code == GraphQLErrorCode.UNAUTHENTICATED
        assert error.safe is True


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_authorization_error(self) -> None:
        """Should instantiate."""
        error = AuthorizationError("Not authorized")
        assert "Not authorized" in str(error)
        assert error.code == GraphQLErrorCode.UNAUTHORIZED
        assert error.safe is True


class TestForbiddenError:
    """Tests for ForbiddenError."""

    def test_forbidden_error(self) -> None:
        """Should instantiate."""
        error = ForbiddenError("Access forbidden")
        assert "Access forbidden" in str(error)
        assert error.code == GraphQLErrorCode.FORBIDDEN
        assert error.safe is True
