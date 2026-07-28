"""Core GraphQL module.

This module provides the core GraphQL execution engine,
schema validation, and introspection capabilities.
"""

from __future__ import annotations

from strawberry import Info

from lexigram.graphql.core.context import (
    GraphQLContext,
    GraphQLRequest,
    GraphQLResponse,
)
from lexigram.graphql.core.error_formatter import (
    ErrorFormatter,
    create_error_formatter,
)
from lexigram.graphql.core.execution import (
    ExecutionContextProtocol,
    GraphQLExecutorProtocol,
    execute_query,
)
from lexigram.graphql.core.introspection import (
    IntrospectionHandler,
    get_introspection_query,
)
from lexigram.graphql.core.validation import (
    SchemaValidator,
    ValidationResult,
    validate_query,
)
from lexigram.graphql.events import (
    AfterExecuteEvent,
    BeforeExecuteEvent,
    OnErrorEvent,
)

__all__ = [
    "AfterExecuteEvent",
    "BeforeExecuteEvent",
    "ErrorFormatter",
    "ExecutionContextProtocol",
    # Context
    "GraphQLContext",
    # Execution
    "GraphQLExecutorProtocol",
    "GraphQLRequest",
    "GraphQLResponse",
    # Info (from strawberry)
    "Info",
    # Introspection
    "IntrospectionHandler",
    "OnErrorEvent",
    # Validation
    "SchemaValidator",
    "ValidationResult",
    "create_error_formatter",
    "execute_query",
    "get_introspection_query",
    "validate_query",
]
