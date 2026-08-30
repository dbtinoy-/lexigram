"""Tests for the models module."""

from __future__ import annotations

import pytest

from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    EntityConfig,
    FeatureFlagConfig,
    JobConfig,
    MiddlewareConfig,
    NodeConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
    RouteGroupConfig,
    ServiceConfig,
)


class TestFrozenDataclasses:
    """All configs must be frozen and slotted."""

    def test_feature_flag_config_frozen(self) -> None:
        config = FeatureFlagConfig(name="test", enabled=True)
        with pytest.raises(AttributeError):
            config.name = "other"  # type: ignore[misc]

    def test_auth_config_frozen(self) -> None:
        config = AuthConfig(name="test", provider="jwt")
        with pytest.raises(AttributeError):
            config.name = "other"  # type: ignore[misc]

    def test_role_config_frozen(self) -> None:
        config = RoleConfig(name="test", permissions=("read",))
        with pytest.raises(AttributeError):
            config.name = "other"  # type: ignore[misc]

    def test_rate_limit_config_frozen(self) -> None:
        config = RateLimitConfig(name="test", max_requests=100)
        with pytest.raises(AttributeError):
            config.name = "other"  # type: ignore[misc]

    def test_contract_config_frozen(self) -> None:
        config = ContractConfig(name="test", direction="request")
        with pytest.raises(AttributeError):
            config.name = "other"  # type: ignore[misc]


class TestFeatureFlagConfig:
    """Tests for FeatureFlagConfig."""

    def test_defaults(self) -> None:
        config = FeatureFlagConfig()
        assert config.name == "new_checkout"
        assert config.enabled is True
        assert config.description == ""

    def test_custom_values(self) -> None:
        config = FeatureFlagConfig(
            name="beta_feature",
            enabled=False,
            description="Beta feature for testing",
        )
        assert config.name == "beta_feature"
        assert config.enabled is False
        assert config.description == "Beta feature for testing"


class TestAuthConfig:
    """Tests for AuthConfig."""

    def test_defaults(self) -> None:
        config = AuthConfig()
        assert config.name == "jwt_auth"
        assert config.provider == "jwt"

    def test_custom_provider(self) -> None:
        config = AuthConfig(name="api_key_auth", provider="api_key")
        assert config.provider == "api_key"


class TestRoleConfig:
    """Tests for RoleConfig."""

    def test_defaults(self) -> None:
        config = RoleConfig()
        assert config.name == "admin"
        assert config.permissions == ()
        assert config.inherits == ""

    def test_with_permissions(self) -> None:
        config = RoleConfig(name="editor", permissions=("read", "write"))
        assert config.permissions == ("read", "write")

    def test_with_inherits(self) -> None:
        config = RoleConfig(name="super_admin", inherits="admin")
        assert config.inherits == "admin"


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_defaults(self) -> None:
        config = RateLimitConfig()
        assert config.name == "api_rate_limit"
        assert config.strategy == "sliding_window"
        assert config.max_requests == 100
        assert config.window_seconds == 60

    def test_custom_values(self) -> None:
        config = RateLimitConfig(
            name="strict_limit",
            strategy="fixed_window",
            max_requests=10,
            window_seconds=30,
        )
        assert config.strategy == "fixed_window"
        assert config.max_requests == 10


class TestContractConfig:
    """Tests for ContractConfig."""

    def test_defaults(self) -> None:
        config = ContractConfig()
        assert config.name == "create_order"
        assert config.direction == "request"
        assert config.fields == "item_id:str, quantity:int"
        assert config.entity == ""
        assert config.enabled is True

    def test_response_direction(self) -> None:
        config = ContractConfig(name="order_view", direction="response")
        assert config.direction == "response"

    def test_both_direction(self) -> None:
        config = ContractConfig(name="order_full", direction="both")
        assert config.direction == "both"

    def test_with_entity(self) -> None:
        config = ContractConfig(name="order_create", entity="order")
        assert config.entity == "order"


class TestNodeConfigUnion:
    """Tests for the NodeConfig union type."""

    def test_all_configs_are_union_members(self) -> None:
        """Verify that all config types are part of the NodeConfig union."""
        import typing

        union_args = typing.get_args(NodeConfig)
        expected_types = {
            RouteConfig,
            RouteGroupConfig,
            EntityConfig,
            ServiceConfig,
            JobConfig,
            MiddlewareConfig,
            FeatureFlagConfig,
            AuthConfig,
            RoleConfig,
            RateLimitConfig,
            ContractConfig,
        }
        assert set(union_args) == expected_types
