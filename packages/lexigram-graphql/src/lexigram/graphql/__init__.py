"""Lexigram GraphQL - GraphQL support for Lexigram Framework.

This package provides GraphQL capabilities for Lexigram Framework applications,
including schema building, execution, subscriptions, and monitoring.
"""

from __future__ import annotations

import importlib.metadata

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

from lexigram.graphql.constants import __version__ as __version__

if TYPE_CHECKING:
    # Types and configuration
    # Provider
    from lexigram.graphql.config import (
        CacheConfig,
        DataLoaderConfig,
        DepthLimitConfig,
        ErrorConfig,
        GraphQLConfig,
        IntrospectionConfig,
        MetricsConfig,
        PlaygroundConfig,
        SubscriptionConfig,
        TracingConfig,
    )

    # Core GraphQL components
    from lexigram.graphql.core.context import (
        ContextFactory,
        GraphQLContext,
        GraphQLRequest,
        GraphQLResponse,
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
    from lexigram.graphql.dataloader.cache import (
        InMemoryCache,
        LoaderCache,
        NoOpCache,
    )

    # DataLoaderProtocol support
    from lexigram.graphql.dataloader.loader import (
        DataLoaderProtocol,
        create_loader,
    )

    # Package-level decorators
    from lexigram.graphql.decorators import log_resolver, retry_resolver
    from lexigram.graphql.di.provider import GraphQLProvider
    from lexigram.graphql.events import (
        AfterExecuteEvent,
        BeforeExecuteEvent,
        OnErrorEvent,
        SchemaBuiltEvent,
        SubscriptionStartedEvent,
    )

    # Errors
    from lexigram.graphql.exceptions import (
        AuthenticationError,
        AuthorizationError,
        ForbiddenError,
        GraphQLError,
        InputGraphQLError,
        NotFoundError,
        ParseError,
        QueryTooComplexError,
        QueryTooDeepError,
        RateLimitError,
        ResolverError,
        SubscriptionError,
    )
    from lexigram.graphql.module import GraphQLModule

    # Monitoring
    from lexigram.graphql.monitoring.metrics import (
        GraphQLMetrics,
        MetricsCollectorProtocol,
        MetricsExtension,
        QueryStats,
        get_metrics_collector,
    )
    from lexigram.graphql.monitoring.tracing import (
        ExecutionTrace,
        TraceSpan,
        TracingExtension,
        trace_resolver,
    )
    from lexigram.graphql.schema.builder import (
        SchemaBuilderProtocol,
        create_schema,
    )

    # Schema decorators and utilities
    from lexigram.graphql.schema.decorators import (
        field,
        get_context,
        mutation,
        query,
        resolver,
        subscription,
    )
    from lexigram.graphql.schema.types import (
        Connection,
        CursorPaginationInput,
        DeleteResult,
        EnumType,
        InputType,
        InterfaceType,
        MutationResult,
        ObjectType,
        PagedResult,
        PaginationInput,
        ScalarType,
        SortInput,
        create_connection_type,
        union_type,
    )
    from lexigram.graphql.security.alias import (
        AliasLimitExtension,
        AliasLimitValidator,
    )

    # Security
    from lexigram.graphql.security.depth import (
        DepthLimitExtension,
        DepthLimitValidator,
        create_depth_limit,
    )
    from lexigram.graphql.security.extensions import RateLimitExtension
    from lexigram.graphql.security.permissions import (
        AbstractPermission,
        AllowAny,
        DenyAll,
        IsAdmin,
        IsAuthenticated,
        IsOwner,
        IsOwnerOrAdmin,
        allow_any,
        deny_all,
        is_admin,
        is_authenticated,
        is_owner,
        is_owner_or_admin,
    )
    from lexigram.graphql.security.rate_limit import (
        RateLimitConfig,
        RateLimiter,
        UnifiedRateLimiter,
    )
    from lexigram.graphql.types import (
        CacheControl,
        CacheScope,
        DataLoaderStats,
        DirectiveLocation,
        FieldInfo,
        GraphQLErrorCode,
        GraphQLErrorData,
        GraphQLErrorExtensions,
        GraphQLLocation,
        OperationInfo,
        OperationType,
        QueryMetrics,
        ResolverInfo,
        SubscriptionInfo,
        SubscriptionProtocol,
    )

_LAZY_IMPORTS = {
    # Module
    "GraphQLModule": "lexigram.graphql.module",
    # Types
    "OperationType": "lexigram.graphql.types",
    "GraphQLErrorCode": "lexigram.graphql.types",
    "DirectiveLocation": "lexigram.graphql.types",
    "CacheScope": "lexigram.graphql.types",
    "SubscriptionProtocol": "lexigram.graphql.types",
    "GraphQLLocation": "lexigram.graphql.types",
    "GraphQLErrorExtensions": "lexigram.graphql.types",
    "GraphQLErrorData": "lexigram.graphql.types",
    "FieldInfo": "lexigram.graphql.types",
    "OperationInfo": "lexigram.graphql.types",
    "ResolverInfo": "lexigram.graphql.types",
    "CacheControl": "lexigram.graphql.types",
    "QueryMetrics": "lexigram.graphql.types",
    "SubscriptionInfo": "lexigram.graphql.types",
    "DataLoaderStats": "lexigram.graphql.types",
    # Config
    "GraphQLConfig": "lexigram.graphql.config",
    "CacheConfig": "lexigram.graphql.config",
    "DepthLimitConfig": "lexigram.graphql.config",
    "IntrospectionConfig": "lexigram.graphql.config",
    "PlaygroundConfig": "lexigram.graphql.config",
    "SubscriptionConfig": "lexigram.graphql.config",
    "DataLoaderConfig": "lexigram.graphql.config",
    "TracingConfig": "lexigram.graphql.config",
    "MetricsConfig": "lexigram.graphql.config",
    "ErrorConfig": "lexigram.graphql.config",
    # Core
    "GraphQLContext": "lexigram.graphql.core.context",
    "GraphQLRequest": "lexigram.graphql.core.context",
    "GraphQLResponse": "lexigram.graphql.core.context",
    "ContextFactory": "lexigram.graphql.core.context",
    "GraphQLExecutorProtocol": "lexigram.graphql.core.execution",
    "ExecutionContextProtocol": "lexigram.graphql.core.execution",
    "execute_query": "lexigram.graphql.core.execution",
    # Events
    "BeforeExecuteEvent": "lexigram.graphql.events",
    "AfterExecuteEvent": "lexigram.graphql.events",
    "OnErrorEvent": "lexigram.graphql.events",
    "SchemaBuiltEvent": "lexigram.graphql.events",
    "SubscriptionStartedEvent": "lexigram.graphql.events",
    "SchemaValidator": "lexigram.graphql.core.validation",
    "ValidationResult": "lexigram.graphql.core.validation",
    "validate_query": "lexigram.graphql.core.validation",
    "IntrospectionHandler": "lexigram.graphql.core.introspection",
    "get_introspection_query": "lexigram.graphql.core.introspection",
    # Decorators
    "log_resolver": "lexigram.graphql.decorators",
    "retry_resolver": "lexigram.graphql.decorators",
    # Schema
    "query": "lexigram.graphql.schema.decorators",
    "mutation": "lexigram.graphql.schema.decorators",
    "subscription": "lexigram.graphql.schema.decorators",
    "resolver": "lexigram.graphql.schema.decorators",
    "field": "lexigram.graphql.schema.decorators",
    "get_context": "lexigram.graphql.schema.decorators",
    "SchemaBuilderProtocol": "lexigram.graphql.schema.builder",
    "create_schema": "lexigram.graphql.schema.builder",
    # Protocol re-exports (contracts + type aliases)
    "GraphQLResolver": "lexigram.graphql.protocols",
    "GraphQLSchema": "lexigram.graphql.protocols",
    "ObjectType": "lexigram.graphql.schema.types",
    "InputType": "lexigram.graphql.schema.types",
    "InterfaceType": "lexigram.graphql.schema.types",
    "union_type": "lexigram.graphql.schema.types",
    "EnumType": "lexigram.graphql.schema.types",
    "ScalarType": "lexigram.graphql.schema.types",
    "Connection": "lexigram.graphql.schema.types",
    "PagedResult": "lexigram.graphql.schema.types",
    "PaginationInput": "lexigram.graphql.schema.types",
    "CursorPaginationInput": "lexigram.graphql.schema.types",
    "SortInput": "lexigram.graphql.schema.types",
    "MutationResult": "lexigram.graphql.schema.types",
    "DeleteResult": "lexigram.graphql.schema.types",
    "create_connection_type": "lexigram.graphql.schema.types",
    # DataLoaderProtocol
    "DataLoaderProtocol": "lexigram.graphql.dataloader.loader",
    "create_loader": "lexigram.graphql.dataloader.loader",
    "LoaderCache": "lexigram.graphql.dataloader.cache",
    "InMemoryCache": "lexigram.graphql.dataloader.cache",
    "NoOpCache": "lexigram.graphql.dataloader.cache",
    # Security
    "DepthLimitExtension": "lexigram.graphql.security.depth",
    "DepthLimitValidator": "lexigram.graphql.security.depth",
    "create_depth_limit": "lexigram.graphql.security.depth",
    "AliasLimitValidator": "lexigram.graphql.security.alias",
    "AbstractPermission": "lexigram.graphql.security.permissions",
    "IsAuthenticated": "lexigram.graphql.security.permissions",
    "IsAdmin": "lexigram.graphql.security.permissions",
    "IsOwner": "lexigram.graphql.security.permissions",
    "IsOwnerOrAdmin": "lexigram.graphql.security.permissions",
    "AllowAny": "lexigram.graphql.security.permissions",
    "DenyAll": "lexigram.graphql.security.permissions",
    "is_authenticated": "lexigram.graphql.security.permissions",
    "is_admin": "lexigram.graphql.security.permissions",
    "is_owner": "lexigram.graphql.security.permissions",
    "is_owner_or_admin": "lexigram.graphql.security.permissions",
    "allow_any": "lexigram.graphql.security.permissions",
    "deny_all": "lexigram.graphql.security.permissions",
    "RateLimiter": "lexigram.graphql.security.rate_limit",
    "RateLimitConfig": "lexigram.graphql.security.rate_limit",
    "UnifiedRateLimiter": "lexigram.graphql.security.rate_limit",
    "RateLimitExtension": "lexigram.graphql.security.extensions",
    # Monitoring
    "GraphQLMetrics": "lexigram.graphql.monitoring.metrics",
    "MetricsCollectorProtocol": "lexigram.graphql.monitoring.metrics",
    "MetricsExtension": "lexigram.graphql.monitoring.metrics",
    "QueryStats": "lexigram.graphql.monitoring.metrics",
    "get_metrics_collector": "lexigram.graphql.monitoring.metrics",
    "TracingExtension": "lexigram.graphql.monitoring.tracing",
    "trace_resolver": "lexigram.graphql.monitoring.tracing",
    "ExecutionTrace": "lexigram.graphql.monitoring.tracing",
    "TraceSpan": "lexigram.graphql.monitoring.tracing",
    # Errors
    "GraphQLError": "lexigram.graphql.exceptions",
    "InputGraphQLError": "lexigram.graphql.exceptions",
    "ResolverError": "lexigram.graphql.exceptions",
    "ParseError": "lexigram.graphql.exceptions",
    "AuthenticationError": "lexigram.graphql.exceptions",
    "AuthorizationError": "lexigram.graphql.exceptions",
    "ForbiddenError": "lexigram.graphql.exceptions",
    "NotFoundError": "lexigram.graphql.exceptions",
    "RateLimitError": "lexigram.graphql.exceptions",
    "QueryTooComplexError": "lexigram.graphql.exceptions",
    "QueryTooDeepError": "lexigram.graphql.exceptions",
    "SubscriptionError": "lexigram.graphql.exceptions",
    "GraphQLConnectionError": "lexigram.graphql.exceptions",
    # Provider
    "GraphQLProvider": "lexigram.graphql.di.provider",
    # Resolvers
    "ResolverAdapter": "lexigram.graphql.resolvers",
    # "resolver" is intentionally omitted here to avoid duplicate keys;
    # it can be imported directly from `lexigram.graphql.resolvers` if needed.
    # Directives
    "DirectiveRegistry": "lexigram.graphql.directives",
    "DeprecationDirectiveHandler": "lexigram.graphql.directives",
    # Pagination
    "Edge": "lexigram.graphql.pagination",
    "PageInfo": "lexigram.graphql.pagination",
    "CursorConnection": "lexigram.graphql.pagination",
    "encode_cursor": "lexigram.graphql.pagination",
    "decode_cursor": "lexigram.graphql.pagination",
    "encode_cursor_from_id": "lexigram.graphql.pagination",
    "decode_cursor_to_id": "lexigram.graphql.pagination",
    # Web Integration
    "GraphQLController": "lexigram.graphql.controllers",
    "GraphQLSubscriptionController": "lexigram.graphql.controllers",
    # APQ
    "PersistedQueryStore": "lexigram.graphql.core.persisted_queries",
    "InMemoryPersistedQueryStore": "lexigram.graphql.core.persisted_queries",
    "RedisPersistedQueryStore": "lexigram.graphql.core.persisted_queries",
    "CacheBackendPersistedQueryStore": "lexigram.graphql.core.persisted_queries",
    "APQResult": "lexigram.graphql.core.persisted_queries",
    "APQHandler": "lexigram.graphql.core.persisted_queries",
    "compute_query_hash": "lexigram.graphql.core.persisted_queries",
    # Hooks
    "GraphQLRequestReceivedHook": "lexigram.graphql.hooks",
    "GraphQLResponsePreparedHook": "lexigram.graphql.hooks",
    "GraphQLSchemaBuiltHook": "lexigram.graphql.hooks",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module_path = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
