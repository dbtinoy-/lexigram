"""GraphQL protocols."""

from __future__ import annotations

from lexigram.contracts.graphql.protocols import (
    DataLoaderProtocol,
    DirectiveHandlerProtocol,
    EntityResolverProtocol,
    ErrorFormatterProtocol,
    GraphQLExecutorProtocol,
    GraphQLPrincipalResolverProtocol,
    GraphQLRequestProtocol,
    IntrospectionHandlerProtocol,
    MutationHandlerProtocol,
    ResolverProtocol,
    SchemaBuilderProtocol,
    SubscriptionAuthHandlerProtocol,
    SubscriptionHandlerProtocol,
    ValidationRuleProtocol,
    WebSocketTransportProtocol,
)
from lexigram.contracts.graphql.types import GraphQLPrincipal

__all__ = [
    "DataLoaderProtocol",
    "DirectiveHandlerProtocol",
    "EntityResolverProtocol",
    "ErrorFormatterProtocol",
    "GraphQLExecutorProtocol",
    "GraphQLPrincipal",
    "GraphQLPrincipalResolverProtocol",
    "GraphQLRequestProtocol",
    "IntrospectionHandlerProtocol",
    "MutationHandlerProtocol",
    "ResolverProtocol",
    "SchemaBuilderProtocol",
    "SubscriptionAuthHandlerProtocol",
    "SubscriptionHandlerProtocol",
    "ValidationRuleProtocol",
    "WebSocketTransportProtocol",
]
