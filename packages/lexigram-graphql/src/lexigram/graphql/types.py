"""Core types and enums for lexigram-graphql.

This module defines all type definitions, enums, and DTOs
used throughout the GraphQL package.

Following the Root File Pattern for easy access:
    from lexigram.graphql.types import OperationType, GraphQLErrorCode
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeVar
from uuid import uuid4

from lexigram.contracts.core import ClockProtocol as _Clock
from lexigram.contracts.core import IdGeneratorProtocol as _Identity


def _now(clock: _Clock | None = None) -> datetime:
    """Get current timestamp using injected clock."""
    if clock is not None:
        return clock.now()
    return datetime.now(UTC)


def _uuid(identity: _Identity | None = None) -> str:
    """Generate a UUID using injected identity."""
    if identity is not None:
        return identity.generate()
    return str(uuid4())


# =============================================================================
# Enums
# =============================================================================


class OperationType(StrEnum):
    """GraphQL operation types."""

    QUERY = "query"
    MUTATION = "mutation"
    SUBSCRIPTION = "subscription"


class GraphQLErrorCode(StrEnum):
    """Standard GraphQL error codes."""

    # Client errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_USER_INPUT = "BAD_USER_INPUT"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"

    # Server errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # GraphQL specific
    GRAPHQL_PARSE_FAILED = "GRAPHQL_PARSE_FAILED"
    GRAPHQL_VALIDATION_FAILED = "GRAPHQL_VALIDATION_FAILED"
    PERSISTED_QUERY_NOT_FOUND = "PERSISTED_QUERY_NOT_FOUND"

    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"
    QUERY_TOO_COMPLEX = "QUERY_TOO_COMPLEX"
    QUERY_TOO_DEEP = "QUERY_TOO_DEEP"


class DirectiveLocation(StrEnum):
    """GraphQL directive locations."""

    # Executable locations
    QUERY = "QUERY"
    MUTATION = "MUTATION"
    SUBSCRIPTION = "SUBSCRIPTION"
    FIELD = "FIELD"
    FRAGMENT_DEFINITION = "FRAGMENT_DEFINITION"
    FRAGMENT_SPREAD = "FRAGMENT_SPREAD"
    INLINE_FRAGMENT = "INLINE_FRAGMENT"
    VARIABLE_DEFINITION = "VARIABLE_DEFINITION"

    # Type system locations
    SCHEMA = "SCHEMA"
    SCALAR = "SCALAR"
    OBJECT = "OBJECT"
    FIELD_DEFINITION = "FIELD_DEFINITION"
    ARGUMENT_DEFINITION = "ARGUMENT_DEFINITION"
    INTERFACE = "INTERFACE"
    UNION = "UNION"
    ENUM = "ENUM"
    ENUM_VALUE = "ENUM_VALUE"
    INPUT_OBJECT = "INPUT_OBJECT"
    INPUT_FIELD_DEFINITION = "INPUT_FIELD_DEFINITION"


class CacheScope(StrEnum):
    """Cache control scope for responses."""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class SubscriptionProtocol(StrEnum):
    """WebSocket subscription protocols."""

    GRAPHQL_WS = "graphql-ws"
    GRAPHQL_TRANSPORT_WS = "graphql-transport-ws"


# =============================================================================
# Data Transfer Objects
# =============================================================================


@dataclass
class GraphQLLocation:
    """Location in a GraphQL document."""

    line: int
    column: int


@dataclass
class GraphQLErrorExtensions:
    """Extended error information."""

    code: str
    timestamp: datetime = field(default_factory=_now)
    request_id: str | None = None
    path: list[str] | None = None
    field: str | None = None
    argument: str | None = None
    exception: str | None = None
    stacktrace: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {"code": self.code}
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        if self.request_id:
            result["requestId"] = self.request_id
        if self.path:
            result["path"] = self.path
        if self.field:
            result["field"] = self.field
        if self.argument:
            result["argument"] = self.argument
        # Only include exception/stacktrace in debug mode
        return result


@dataclass
class GraphQLErrorData:
    """Structured GraphQL error data."""

    message: str
    locations: list[GraphQLLocation] | None = None
    path: list[str | int] | None = None
    extensions: GraphQLErrorExtensions | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to standard GraphQL error format."""
        result: dict[str, Any] = {"message": self.message}

        if self.locations:
            result["locations"] = [
                {"line": loc.line, "column": loc.column} for loc in self.locations
            ]

        if self.path:
            result["path"] = self.path

        if self.extensions:
            result["extensions"] = self.extensions.to_dict()

        return result


@dataclass
class FieldInfo:
    """Information about a GraphQL field."""

    name: str
    parent_type: str
    return_type: str
    arguments: dict[str, Any] = field(default_factory=dict)
    directives: list[str] = field(default_factory=list)
    is_nullable: bool = True
    is_list: bool = False
    deprecation_reason: str | None = None


@dataclass
class OperationInfo:
    """Information about a GraphQL operation."""

    name: str | None
    operation_type: OperationType
    variables: dict[str, Any] = field(default_factory=dict)
    selection_count: int = 0
    depth: int = 0
    complexity: int = 0


@dataclass
class ResolverInfo:
    """Context information passed to resolvers."""

    field_name: str
    parent_type: str
    return_type: str
    path: list[str | int]
    operation: OperationInfo
    variables: dict[str, Any]
    context: Any
    root_value: Any = None


@dataclass
class CacheControl:
    """Cache control settings for a field or type."""

    max_age: int = 0
    scope: CacheScope = CacheScope.PUBLIC
    inherit_max_age: bool = False

    def to_header(self) -> str:
        """Generate Cache-Control header value."""
        parts = []
        if self.scope == CacheScope.PRIVATE:
            parts.append("private")
        else:
            parts.append("public")
        parts.append(f"max-age={self.max_age}")
        return ", ".join(parts)


@dataclass
class QueryMetrics:
    """Metrics for a GraphQL query execution."""

    request_id: str = field(default_factory=_uuid)
    operation_name: str | None = None
    operation_type: OperationType | None = None
    started_at: datetime = field(default_factory=_now)
    ended_at: datetime | None = None
    duration_ms: float = 0.0
    field_count: int = 0
    depth: int = 0
    complexity: int = 0
    errors_count: int = 0
    cache_hit: bool = False

    def complete(self) -> None:
        """Mark the query as complete and calculate duration."""
        self.ended_at = _now()
        self.duration_ms = (self.ended_at - self.started_at).total_seconds() * 1000


@dataclass
class SubscriptionInfo:
    """Information about an active subscription."""

    subscription_id: str
    operation_name: str | None
    query: str
    variables: dict[str, Any]
    created_at: datetime = field(default_factory=_now)
    last_event_at: datetime | None = None
    event_count: int = 0


@dataclass
class DataLoaderStats:
    """Statistics for a DataLoaderProtocol instance."""

    name: str
    batch_count: int = 0
    load_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# Handler types
ResolverFunc = Callable[..., Any]
MiddlewareFunc = Callable[[ResolverInfo, Callable], Any]
ErrorHandler = Callable[[Exception, ResolverInfo], GraphQLErrorData]


__all__ = [
    "CacheControl",
    "CacheScope",
    "DataLoaderStats",
    "DirectiveLocation",
    "ErrorHandler",
    "FieldInfo",
    "GraphQLErrorCode",
    "GraphQLErrorData",
    "GraphQLErrorExtensions",
    # DTOs
    "GraphQLLocation",
    "K",
    "MiddlewareFunc",
    "OperationInfo",
    # Enums
    "OperationType",
    "QueryMetrics",
    "ResolverFunc",
    "ResolverInfo",
    "SubscriptionInfo",
    "SubscriptionProtocol",
    # Type vars
    "T",
    "V",
]
