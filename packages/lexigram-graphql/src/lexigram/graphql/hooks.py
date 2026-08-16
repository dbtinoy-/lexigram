"""Root hook payload surface for lexigram-graphql.

Defines canonical payload dataclasses for GraphQL lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GraphQLRequestReceivedHook",
    "GraphQLResponsePreparedHook",
    "GraphQLSchemaBuiltHook",
]


@dataclass(frozen=True, kw_only=True)
class GraphQLSchemaBuiltHook:
    """Payload fired after the GraphQL schema has been compiled and is ready."""


@dataclass(frozen=True, kw_only=True)
class GraphQLRequestReceivedHook:
    """Payload fired when a GraphQL operation request is received.

    Attributes:
        operation_type: ``"query"``, ``"mutation"``, or ``"subscription"``.
        operation_name: Named operation, if present in the document.
    """

    operation_type: str
    operation_name: str | None = None


@dataclass(frozen=True, kw_only=True)
class GraphQLResponsePreparedHook:
    """Payload fired after a GraphQL response has been assembled.

    Attributes:
        operation_type: ``"query"``, ``"mutation"``, or ``"subscription"``.
        has_errors: ``True`` if the response contains any GraphQL errors.
    """

    operation_type: str
    has_errors: bool
