"""GraphQL protocol re-exports.

Central contract imports for the lexigram-graphql package.
All protocol definitions live in ``lexigram.contracts.graphql``; this module
re-exports the ones that are relevant to consumers of lexigram-graphql so
they can import from a single, stable location.

Canonical protocols (from contracts):
    SchemaBuilderProtocol   - fluent schema-building contract
    GraphQLExecutorProtocol - execution contract
    ErrorFormatter  - error formatting contract
    DataLoaderProtocol      - batch-loading contract
    ResolverProtocol        - field-resolver contract
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from strawberry import Schema

from lexigram.contracts.graphql import (
    DataLoaderProtocol,
    DirectiveHandlerProtocol,
    ErrorFormatterProtocol,
    GraphQLExecutorProtocol,
    ResolverProtocol,
    SchemaBuilderProtocol,
    SubscriptionAuthHandlerProtocol,
    SubscriptionHandlerProtocol,
    ValidationRuleProtocol,
)
from lexigram.graphql.directives import DeprecationDirectiveHandler, DirectiveRegistry
from lexigram.graphql.resolvers import ResolverAdapter, resolver

# ---------------------------------------------------------------------------
# Public type aliases
# ---------------------------------------------------------------------------

# A GraphQL schema instance (Strawberry Schema).
GraphQLSchema = Schema

# A resolver callable — any function that accepts (parent, args, context, info)
# and returns Any (sync or async).  Kept as a broad alias to avoid coupling to
# a specific resolver protocol where plain functions are used.
GraphQLResolver = Callable[..., Any]


__all__ = [
    # Contracts re-exports
    "DataLoaderProtocol",
    "DeprecationDirectiveHandler",
    "DirectiveHandlerProtocol",
    "ErrorFormatterProtocol",
    "GraphQLExecutorProtocol",
    "ResolverProtocol",
    "SchemaBuilderProtocol",
    "SubscriptionHandlerProtocol",
    "ValidationRuleProtocol",
    "WebSocketTransportProtocol",
    "resolver",
]
