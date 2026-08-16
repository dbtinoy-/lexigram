"""GraphQL exceptions - complete exception hierarchy."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions import (
    AuthenticationError as _ContractsAuthenticationError,
)
from lexigram.contracts.exceptions import (
    AuthorizationError as _ContractsAuthorizationError,
)
from lexigram.contracts.exceptions import LexigramError
from lexigram.graphql.types import GraphQLErrorCode


class GraphQLError(LexigramError):
    """Base exception for all GraphQL errors."""

    _code: str = "LEX_ERR_GQL_001"
    code: GraphQLErrorCode = GraphQLErrorCode.INTERNAL_SERVER_ERROR
    safe: bool = False  # Whether error message can be shown to users

    def __init__(
        self, message: str, *, code: GraphQLErrorCode | None = None, **kwargs: Any
    ) -> None:
        # Use class attribute code if not explicitly provided
        effective_code = code if code is not None else self.__class__.code
        super().__init__(message)
        self.code = effective_code
        self.extensions = kwargs


class ExecutionError(GraphQLError):
    """Raised when execution fails."""

    _code: str = "LEX_ERR_GQL_002"


class GraphQLTimeoutError(ExecutionError):
    """Raised when execution times out."""

    _code: str = "LEX_ERR_GQL_003"


class QueryTooDeepError(GraphQLError):
    """Raised when a GraphQL query exceeds the maximum depth."""

    _code: str = "LEX_ERR_GQL_004"
    code = GraphQLErrorCode.QUERY_TOO_DEEP
    safe = True


# --- Validation ---
class InputGraphQLError(GraphQLError):
    """Raised for invalid user input."""

    _code: str = "LEX_ERR_GQL_005"
    code = GraphQLErrorCode.BAD_USER_INPUT
    safe = True


class ParseError(GraphQLError):
    """Raised when query parsing fails."""

    _code: str = "LEX_ERR_GQL_006"
    code = GraphQLErrorCode.GRAPHQL_PARSE_FAILED


class QueryTooComplexError(GraphQLError):
    """Raised when query exceeds complexity limit."""

    _code: str = "LEX_ERR_GQL_007"
    code = GraphQLErrorCode.QUERY_TOO_COMPLEX
    safe = True


class ResolverError(GraphQLError):
    """Raised when a resolver fails."""

    _code: str = "LEX_ERR_GQL_008"


# --- Auth ---
class AuthenticationError(GraphQLError, _ContractsAuthenticationError):
    """Raised when authentication is required but missing.

    Also satisfies ``lexigram.contracts.exceptions.AuthenticationError`` so
    middleware that catches the contracts type will catch this as well.
    """

    _code: str = "LEX_ERR_GQL_009"
    code = GraphQLErrorCode.UNAUTHENTICATED
    safe = True


class AuthorizationError(GraphQLError, _ContractsAuthorizationError):
    """Raised when user is authenticated but lacks permissions.

    Also satisfies ``lexigram.contracts.exceptions.AuthorizationError`` so
    middleware that catches the contracts type will catch this as well.
    """

    _code: str = "LEX_ERR_GQL_010"
    code = GraphQLErrorCode.UNAUTHORIZED
    safe = True


class ForbiddenError(GraphQLError):
    """Raised when access is forbidden."""

    _code: str = "LEX_ERR_GQL_011"
    code = GraphQLErrorCode.FORBIDDEN
    safe = True


class NotFoundError(GraphQLError):
    """Raised when a requested resource is not found."""

    _code: str = "LEX_ERR_GQL_012"
    code = GraphQLErrorCode.NOT_FOUND
    safe = True


# --- Security ---
class RateLimitError(GraphQLError):
    """Raised when rate limit is exceeded."""

    _code: str = "LEX_ERR_GQL_013"
    code = GraphQLErrorCode.RATE_LIMITED
    safe = True


# --- Subscriptions ---
class SubscriptionError(GraphQLError):
    """Raised for subscription-related errors."""

    _code: str = "LEX_ERR_GQL_014"


# --- Network ---
class GraphQLConnectionError(GraphQLError):
    """Raised when a network connection error occurs during GraphQL execution."""

    _code: str = "LEX_ERR_GQL_015"


__all__ = [
    # Auth
    "AuthenticationError",
    "AuthorizationError",
    # Execution
    "ExecutionError",
    "ForbiddenError",
    # Network
    "GraphQLConnectionError",
    # Base
    "GraphQLError",
    "GraphQLTimeoutError",
    # Validation
    "InputGraphQLError",
    "NotFoundError",
    "ParseError",
    "QueryTooComplexError",
    "QueryTooDeepError",
    # Security
    "RateLimitError",
    "ResolverError",
    # Subscriptions
    "SubscriptionError",
]
