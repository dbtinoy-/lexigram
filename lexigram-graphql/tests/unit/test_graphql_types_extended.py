"""Tests for additional GraphQL types and enums."""

import pytest

from lexigram.graphql.types import (
    CacheControl,
    CacheScope,
    DataLoaderStats,
    DirectiveLocation,
    GraphQLLocation,
    GraphQLErrorExtensions,
    GraphQLErrorData,
    OperationInfo,
    OperationType,
    QueryMetrics,
    ResolverInfo,
    SubscriptionInfo,
    SubscriptionProtocol,
)


class TestCacheScope:
    """Tests for CacheScope enum."""

    def test_cache_scope_values(self) -> None:
        """Test CacheScope enum values."""
        assert CacheScope.PUBLIC.value == "PUBLIC"
        assert CacheScope.PRIVATE.value == "PRIVATE"

    def test_cache_scope_members(self) -> None:
        """Test CacheScope has expected members."""
        members = list(CacheScope)
        assert len(members) == 2

    def test_cache_scope_from_string(self) -> None:
        """Test creating CacheScope from string."""
        assert CacheScope("PUBLIC") == CacheScope.PUBLIC
        assert CacheScope("PRIVATE") == CacheScope.PRIVATE


class TestDirectiveLocation:
    """Tests for DirectiveLocation enum."""

    def test_directive_location_executable(self) -> None:
        """Test DirectiveLocation executable locations."""
        assert DirectiveLocation.QUERY.value == "QUERY"
        assert DirectiveLocation.MUTATION.value == "MUTATION"
        assert DirectiveLocation.SUBSCRIPTION.value == "SUBSCRIPTION"
        assert DirectiveLocation.FIELD.value == "FIELD"

    def test_directive_location_type_system(self) -> None:
        """Test DirectiveLocation type system locations."""
        assert DirectiveLocation.SCHEMA.value == "SCHEMA"
        assert DirectiveLocation.SCALAR.value == "SCALAR"
        assert DirectiveLocation.OBJECT.value == "OBJECT"
        assert DirectiveLocation.INTERFACE.value == "INTERFACE"

    def test_directive_location_members(self) -> None:
        """Test DirectiveLocation has expected members."""
        members = list(DirectiveLocation)
        assert len(members) >= 16


class TestSubscriptionProtocol:
    """Tests for SubscriptionProtocol enum."""

    def test_subscription_protocol_values(self) -> None:
        """Test SubscriptionProtocol enum values."""
        assert SubscriptionProtocol.GRAPHQL_WS.value == "graphql-ws"
        assert SubscriptionProtocol.GRAPHQL_TRANSPORT_WS.value == "graphql-transport-ws"

    def test_subscription_protocol_members(self) -> None:
        """Test SubscriptionProtocol has expected members."""
        members = list(SubscriptionProtocol)
        assert len(members) == 2


class TestGraphQLLocation:
    """Tests for GraphQLLocation dataclass."""

    def test_graphql_location_creation(self) -> None:
        """Test creating GraphQLLocation."""
        location = GraphQLLocation(line=1, column=10)
        assert location.line == 1
        assert location.column == 10


class TestGraphQLErrorExtensions:
    """Tests for GraphQLErrorExtensions dataclass."""

    def test_error_extensions_creation(self) -> None:
        """Test creating GraphQLErrorExtensions."""
        ext = GraphQLErrorExtensions(code="VALIDATION_ERROR")
        assert ext.code == "VALIDATION_ERROR"
        assert ext.timestamp is not None
        assert ext.request_id is None

    def test_error_extensions_to_dict(self) -> None:
        """Test GraphQLErrorExtensions to_dict."""
        ext = GraphQLErrorExtensions(
            code="VALIDATION_ERROR",
            request_id="req-123",
            field="username",
        )
        data = ext.to_dict()
        assert data["code"] == "VALIDATION_ERROR"
        assert data["requestId"] == "req-123"
        assert data["field"] == "username"


class TestGraphQLErrorData:
    """Tests for GraphQLErrorData dataclass."""

    def test_error_data_creation(self) -> None:
        """Test creating GraphQLErrorData."""
        error = GraphQLErrorData(message="Validation failed")
        assert error.message == "Validation failed"
        assert error.locations is None

    def test_error_data_with_location(self) -> None:
        """Test GraphQLErrorData with location."""
        locations = [GraphQLLocation(line=1, column=5)]
        error = GraphQLErrorData(
            message="Validation failed",
            locations=locations,
        )
        assert error.locations is not None
        assert len(error.locations) == 1

    def test_error_data_to_dict(self) -> None:
        """Test GraphQLErrorData to_dict."""
        error = GraphQLErrorData(
            message="Validation failed",
            locations=[GraphQLLocation(line=1, column=5)],
        )
        data = error.to_dict()
        assert data["message"] == "Validation failed"
        assert "locations" in data


class TestCacheControl:
    """Tests for CacheControl dataclass."""

    def test_cache_control_defaults(self) -> None:
        """Test CacheControl default values."""
        cc = CacheControl()
        assert cc.max_age == 0
        assert cc.scope == CacheScope.PUBLIC
        assert cc.inherit_max_age is False

    def test_cache_control_to_header_public(self) -> None:
        """Test CacheControl to_header for public."""
        cc = CacheControl(max_age=300, scope=CacheScope.PUBLIC)
        header = cc.to_header()
        assert "public" in header
        assert "max-age=300" in header

    def test_cache_control_to_header_private(self) -> None:
        """Test CacheControl to_header for private."""
        cc = CacheControl(max_age=60, scope=CacheScope.PRIVATE)
        header = cc.to_header()
        assert "private" in header
        assert "max-age=60" in header


class TestQueryMetrics:
    """Tests for QueryMetrics dataclass."""

    def test_query_metrics_creation(self) -> None:
        """Test creating QueryMetrics."""
        metrics = QueryMetrics()
        assert metrics.request_id is not None
        assert metrics.started_at is not None
        assert metrics.duration_ms == 0.0

    def test_query_metrics_complete(self) -> None:
        """Test QueryMetrics complete method."""
        metrics = QueryMetrics()
        metrics.complete()
        assert metrics.ended_at is not None
        assert metrics.duration_ms > 0


class TestSubscriptionInfo:
    """Tests for SubscriptionInfo dataclass."""

    def test_subscription_info_creation(self) -> None:
        """Test creating SubscriptionInfo."""
        info = SubscriptionInfo(
            subscription_id="sub-123",
            operation_name="onMessage",
            query="subscription { onMessage { text } }",
            variables={},
        )
        assert info.subscription_id == "sub-123"
        assert info.event_count == 0
        assert info.created_at is not None


class TestDataLoaderStats:
    """Tests for DataLoaderStats dataclass."""

    def test_data_loader_stats_creation(self) -> None:
        """Test creating DataLoaderStats."""
        stats = DataLoaderStats(name="user_loader")
        assert stats.name == "user_loader"
        assert stats.batch_count == 0

    def test_cache_hit_ratio_zero(self) -> None:
        """Test cache hit ratio when no hits or misses."""
        stats = DataLoaderStats(name="test")
        assert stats.cache_hit_ratio == 0.0

    def test_cache_hit_ratio_calculated(self) -> None:
        """Test cache hit ratio calculation."""
        stats = DataLoaderStats(
            name="test",
            cache_hits=80,
            cache_misses=20,
        )
        assert stats.cache_hit_ratio == 0.8


class TestOperationInfo:
    """Tests for OperationInfo dataclass."""

    def test_operation_info_creation(self) -> None:
        """Test creating OperationInfo."""
        info = OperationInfo(
            name="GetUser",
            operation_type=OperationType.QUERY,
            variables={"id": "123"},
        )
        assert info.name == "GetUser"
        assert info.operation_type == OperationType.QUERY
        assert info.depth == 0


class TestResolverInfo:
    """Tests for ResolverInfo dataclass."""

    def test_resolver_info_creation(self) -> None:
        """Test creating ResolverInfo."""
        op_info = OperationInfo(
            name="GetUser",
            operation_type=OperationType.QUERY,
        )
        info = ResolverInfo(
            field_name="username",
            parent_type="User",
            return_type="String",
            path=["user", "username"],
            operation=op_info,
            variables={},
            context={},
        )
        assert info.field_name == "username"
        assert info.parent_type == "User"
