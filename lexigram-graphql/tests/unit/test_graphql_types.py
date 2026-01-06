"""Tests for GraphQL types enums, dataclasses, and type aliases."""

import pytest
from datetime import datetime, timezone
from lexigram.graphql.types import (
    OperationType,
    GraphQLErrorCode,
    DirectiveLocation,
    CacheScope,
    SubscriptionProtocol,
    GraphQLLocation,
    GraphQLErrorExtensions,
    GraphQLErrorData,
    FieldInfo,
    OperationInfo,
    ResolverInfo,
    CacheControl,
    QueryMetrics,
    SubscriptionInfo,
    DataLoaderStats,
    ResolverFunc,
    MiddlewareFunc,
    ErrorHandler,
    T,
    K,
    V,
)


class TestOperationType:
    def test_query(self) -> None:
        assert OperationType.QUERY == "query"

    def test_mutation(self) -> None:
        assert OperationType.MUTATION == "mutation"

    def test_subscription(self) -> None:
        assert OperationType.SUBSCRIPTION == "subscription"

    def test_is_str_enum(self) -> None:
        assert isinstance(OperationType.QUERY, str)


class TestGraphQLErrorCode:
    def test_validation_error(self) -> None:
        assert GraphQLErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"

    def test_bad_user_input(self) -> None:
        assert GraphQLErrorCode.BAD_USER_INPUT == "BAD_USER_INPUT"

    def test_unauthenticated(self) -> None:
        assert GraphQLErrorCode.UNAUTHENTICATED == "UNAUTHENTICATED"

    def test_unauthorized(self) -> None:
        assert GraphQLErrorCode.UNAUTHORIZED == "UNAUTHORIZED"

    def test_forbidden(self) -> None:
        assert GraphQLErrorCode.FORBIDDEN == "FORBIDDEN"

    def test_not_found(self) -> None:
        assert GraphQLErrorCode.NOT_FOUND == "NOT_FOUND"

    def test_internal_server_error(self) -> None:
        assert GraphQLErrorCode.INTERNAL_SERVER_ERROR == "INTERNAL_SERVER_ERROR"

    def test_service_unavailable(self) -> None:
        assert GraphQLErrorCode.SERVICE_UNAVAILABLE == "SERVICE_UNAVAILABLE"

    def test_graphql_parse_failed(self) -> None:
        assert GraphQLErrorCode.GRAPHQL_PARSE_FAILED == "GRAPHQL_PARSE_FAILED"

    def test_graphql_validation_failed(self) -> None:
        assert GraphQLErrorCode.GRAPHQL_VALIDATION_FAILED == "GRAPHQL_VALIDATION_FAILED"

    def test_persisted_query_not_found(self) -> None:
        assert GraphQLErrorCode.PERSISTED_QUERY_NOT_FOUND == "PERSISTED_QUERY_NOT_FOUND"

    def test_rate_limited(self) -> None:
        assert GraphQLErrorCode.RATE_LIMITED == "RATE_LIMITED"

    def test_query_too_complex(self) -> None:
        assert GraphQLErrorCode.QUERY_TOO_COMPLEX == "QUERY_TOO_COMPLEX"

    def test_query_too_deep(self) -> None:
        assert GraphQLErrorCode.QUERY_TOO_DEEP == "QUERY_TOO_DEEP"

    def test_is_str_enum(self) -> None:
        assert isinstance(GraphQLErrorCode.VALIDATION_ERROR, str)


class TestDirectiveLocation:
    def test_executable_locations(self) -> None:
        assert DirectiveLocation.QUERY == "QUERY"
        assert DirectiveLocation.MUTATION == "MUTATION"
        assert DirectiveLocation.SUBSCRIPTION == "SUBSCRIPTION"
        assert DirectiveLocation.FIELD == "FIELD"
        assert DirectiveLocation.FRAGMENT_DEFINITION == "FRAGMENT_DEFINITION"
        assert DirectiveLocation.FRAGMENT_SPREAD == "FRAGMENT_SPREAD"
        assert DirectiveLocation.INLINE_FRAGMENT == "INLINE_FRAGMENT"
        assert DirectiveLocation.VARIABLE_DEFINITION == "VARIABLE_DEFINITION"

    def test_type_system_locations(self) -> None:
        assert DirectiveLocation.SCHEMA == "SCHEMA"
        assert DirectiveLocation.SCALAR == "SCALAR"
        assert DirectiveLocation.OBJECT == "OBJECT"
        assert DirectiveLocation.FIELD_DEFINITION == "FIELD_DEFINITION"
        assert DirectiveLocation.ARGUMENT_DEFINITION == "ARGUMENT_DEFINITION"
        assert DirectiveLocation.INTERFACE == "INTERFACE"
        assert DirectiveLocation.UNION == "UNION"
        assert DirectiveLocation.ENUM == "ENUM"
        assert DirectiveLocation.ENUM_VALUE == "ENUM_VALUE"
        assert DirectiveLocation.INPUT_OBJECT == "INPUT_OBJECT"
        assert DirectiveLocation.INPUT_FIELD_DEFINITION == "INPUT_FIELD_DEFINITION"


class TestCacheScope:
    def test_public(self) -> None:
        assert CacheScope.PUBLIC == "PUBLIC"

    def test_private(self) -> None:
        assert CacheScope.PRIVATE == "PRIVATE"


class TestSubscriptionProtocol:
    def test_graphql_ws(self) -> None:
        assert SubscriptionProtocol.GRAPHQL_WS == "graphql-ws"

    def test_graphql_transport_ws(self) -> None:
        assert SubscriptionProtocol.GRAPHQL_TRANSPORT_WS == "graphql-transport-ws"


class TestGraphQLLocation:
    def test_creation(self) -> None:
        loc = GraphQLLocation(line=1, column=5)
        assert loc.line == 1
        assert loc.column == 5


class TestGraphQLErrorExtensions:
    def test_creation(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR")
        assert ext.code == "TEST_ERROR"
        assert ext.timestamp is not None

    def test_to_dict_basic(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR")
        result = ext.to_dict()
        assert result["code"] == "TEST_ERROR"
        assert "timestamp" in result

    def test_to_dict_with_request_id(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR", request_id="req-123")
        result = ext.to_dict()
        assert result["requestId"] == "req-123"

    def test_to_dict_with_path(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR", path=["users", 0])
        result = ext.to_dict()
        assert result["path"] == ["users", 0]

    def test_to_dict_with_field(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR", field="email")
        result = ext.to_dict()
        assert result["field"] == "email"

    def test_to_dict_with_argument(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR", argument="id")
        result = ext.to_dict()
        assert result["argument"] == "id"


class TestGraphQLErrorData:
    def test_creation(self) -> None:
        error = GraphQLErrorData(message="Test error")
        assert error.message == "Test error"
        assert error.locations is None
        assert error.path is None
        assert error.extensions is None

    def test_to_dict_basic(self) -> None:
        error = GraphQLErrorData(message="Test error")
        result = error.to_dict()
        assert result["message"] == "Test error"

    def test_to_dict_with_locations(self) -> None:
        error = GraphQLErrorData(
            message="Test error",
            locations=[GraphQLLocation(line=1, column=5)],
        )
        result = error.to_dict()
        assert result["locations"] == [{"line": 1, "column": 5}]

    def test_to_dict_with_path(self) -> None:
        error = GraphQLErrorData(message="Test error", path=["users", 0])
        result = error.to_dict()
        assert result["path"] == ["users", 0]

    def test_to_dict_with_extensions(self) -> None:
        ext = GraphQLErrorExtensions(code="TEST_ERROR")
        error = GraphQLErrorData(message="Test error", extensions=ext)
        result = error.to_dict()
        assert result["extensions"]["code"] == "TEST_ERROR"


class TestFieldInfo:
    def test_creation(self) -> None:
        info = FieldInfo(
            name="username",
            parent_type="User",
            return_type="String",
        )
        assert info.name == "username"
        assert info.parent_type == "User"
        assert info.return_type == "String"
        assert info.is_nullable is True
        assert info.is_list is False

    def test_with_arguments(self) -> None:
        info = FieldInfo(
            name="user",
            parent_type="Query",
            return_type="User",
            arguments={"id": "ID!"},
        )
        assert info.arguments == {"id": "ID!"}


class TestOperationInfo:
    def test_creation(self) -> None:
        info = OperationInfo(
            name="GetUser",
            operation_type=OperationType.QUERY,
        )
        assert info.name == "GetUser"
        assert info.operation_type == OperationType.QUERY
        assert info.selection_count == 0
        assert info.depth == 0
        assert info.complexity == 0


class TestResolverInfo:
    def test_creation(self) -> None:
        op_info = OperationInfo(name="GetUser", operation_type=OperationType.QUERY)
        info = ResolverInfo(
            field_name="username",
            parent_type="User",
            return_type="String",
            path=["user"],
            operation=op_info,
            variables={},
            context=None,
        )
        assert info.field_name == "username"
        assert info.parent_type == "User"


class TestCacheControl:
    def test_creation_defaults(self) -> None:
        cc = CacheControl()
        assert cc.max_age == 0
        assert cc.scope == CacheScope.PUBLIC

    def test_to_header_public(self) -> None:
        cc = CacheControl(max_age=300, scope=CacheScope.PUBLIC)
        assert cc.to_header() == "public, max-age=300"

    def test_to_header_private(self) -> None:
        cc = CacheControl(max_age=60, scope=CacheScope.PRIVATE)
        assert cc.to_header() == "private, max-age=60"


class TestQueryMetrics:
    def test_creation(self) -> None:
        metrics = QueryMetrics()
        assert metrics.request_id is not None
        assert metrics.duration_ms == 0.0

    def test_complete(self) -> None:
        metrics = QueryMetrics()
        metrics.complete()
        assert metrics.ended_at is not None
        assert metrics.duration_ms > 0


class TestSubscriptionInfo:
    def test_creation(self) -> None:
        info = SubscriptionInfo(
            subscription_id="sub-123",
            operation_name="OnUserUpdate",
            query="subscription { ... }",
            variables={},
        )
        assert info.subscription_id == "sub-123"
        assert info.event_count == 0


class TestDataLoaderStats:
    def test_creation(self) -> None:
        stats = DataLoaderStats(name="user_loader")
        assert stats.name == "user_loader"
        assert stats.cache_hit_ratio == 0.0

    def test_cache_hit_ratio_with_hits(self) -> None:
        stats = DataLoaderStats(name="user_loader", cache_hits=80, cache_misses=20)
        assert stats.cache_hit_ratio == 0.8

    def test_cache_hit_ratio_no_data(self) -> None:
        stats = DataLoaderStats(name="user_loader")
        assert stats.cache_hit_ratio == 0.0