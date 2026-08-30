"""Tests for the validation module."""

from __future__ import annotations

import pytest

from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    EntityConfig,
    FeatureFlagConfig,
    JobConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
)
from lexigram_builder.graph.validation import (
    AUTH_PROVIDERS,
    CONTRACT_DIRECTIONS,
    FIELD_TYPES,
    RATE_LIMIT_STRATEGIES,
    check_document,
    check_edge,
    check_node,
    is_snake_case_identifier,
)


class TestIsSnakeCaseIdentifier:
    """Tests for is_snake_case_identifier."""

    @pytest.mark.parametrize(
        "value",
        ["new_checkout", "admin", "api_rate_limit", "a", "my_feature_v2"],
    )
    def test_valid_snake_case(self, value: str) -> None:
        assert is_snake_case_identifier(value) is True

    @pytest.mark.parametrize(
        "value",
        ["NewCheckout", "admin-role", "123abc", "_private", "has space", ""],
    )
    def test_invalid_snake_case(self, value: str) -> None:
        assert is_snake_case_identifier(value) is False


class TestCheckRoute:
    """Tests for route validation."""

    def test_valid_route(self) -> None:
        config = RouteConfig(path="/api/items")
        assert check_node("route", config) == []

    def test_route_path_must_start_with_slash(self) -> None:
        config = RouteConfig(path="api/items")
        errors = check_node("route", config)
        assert any("must start with '/'" in e for e in errors)

    def test_route_unknown_ops(self) -> None:
        config = RouteConfig(path="/api/items", ops=("create", "fly"))
        errors = check_node("route", config)
        assert any("unknown operations" in e for e in errors)


class TestCheckEntity:
    """Tests for entity validation."""

    def test_valid_entity(self) -> None:
        config = EntityConfig(name="user", fields="name:str, email:str")
        assert check_node("entity", config) == []

    def test_entity_bad_name(self) -> None:
        config = EntityConfig(name="User", fields="name:str")
        errors = check_node("entity", config)
        assert any("snake_case" in e for e in errors)

    def test_entity_bad_field_type(self) -> None:
        config = EntityConfig(name="user", fields="name:str, age:integer")
        errors = check_node("entity", config)
        assert any("unknown type" in e for e in errors)


class TestCheckFeatureFlag:
    """Tests for feature_flag validation (Workstream A)."""

    def test_valid_feature_flag(self) -> None:
        config = FeatureFlagConfig(name="new_checkout")
        assert check_node("feature_flag", config) == []

    def test_feature_flag_bad_name(self) -> None:
        config = FeatureFlagConfig(name="NewCheckout")
        errors = check_node("feature_flag", config)
        assert any("snake_case" in e for e in errors)

    def test_feature_flag_empty_name(self) -> None:
        config = FeatureFlagConfig(name="")
        errors = check_node("feature_flag", config)
        assert any("snake_case" in e for e in errors)


class TestCheckAuth:
    """Tests for auth validation (Workstream B)."""

    def test_valid_auth(self) -> None:
        config = AuthConfig(name="jwt_auth", provider="jwt")
        assert check_node("auth", config) == []

    def test_auth_bad_name(self) -> None:
        config = AuthConfig(name="JWT-Auth", provider="jwt")
        errors = check_node("auth", config)
        assert any("snake_case" in e for e in errors)

    def test_auth_bad_provider(self) -> None:
        config = AuthConfig(name="test", provider="magic")
        errors = check_node("auth", config)
        assert any("provider" in e for e in errors)

    @pytest.mark.parametrize("provider", sorted(AUTH_PROVIDERS))
    def test_auth_all_providers_valid(self, provider: str) -> None:
        config = AuthConfig(name="test", provider=provider)
        assert check_node("auth", config) == []


class TestCheckRole:
    """Tests for role validation (Workstream B)."""

    def test_valid_role(self) -> None:
        config = RoleConfig(name="admin", permissions=("read", "write"))
        assert check_node("role", config) == []

    def test_role_bad_name(self) -> None:
        config = RoleConfig(name="Admin")
        errors = check_node("role", config)
        assert any("snake_case" in e for e in errors)

    def test_role_bad_inherits(self) -> None:
        config = RoleConfig(name="admin", inherits="Super-Admin")
        errors = check_node("role", config)
        assert any("inherits" in e for e in errors)

    def test_role_empty_inherits_ok(self) -> None:
        config = RoleConfig(name="admin", inherits="")
        assert check_node("role", config) == []


class TestCheckRateLimit:
    """Tests for rate_limit validation (Workstream B)."""

    def test_valid_rate_limit(self) -> None:
        config = RateLimitConfig(name="api_limit")
        assert check_node("rate_limit", config) == []

    def test_rate_limit_bad_name(self) -> None:
        config = RateLimitConfig(name="API-Limit")
        errors = check_node("rate_limit", config)
        assert any("snake_case" in e for e in errors)

    def test_rate_limit_bad_strategy(self) -> None:
        config = RateLimitConfig(name="test", strategy="magic")
        errors = check_node("rate_limit", config)
        assert any("strategy" in e for e in errors)

    def test_rate_limit_zero_max_requests(self) -> None:
        config = RateLimitConfig(name="test", max_requests=0)
        errors = check_node("rate_limit", config)
        assert any("positive" in e for e in errors)

    def test_rate_limit_negative_window(self) -> None:
        config = RateLimitConfig(name="test", window_seconds=-1)
        errors = check_node("rate_limit", config)
        assert any("positive" in e for e in errors)

    @pytest.mark.parametrize("strategy", sorted(RATE_LIMIT_STRATEGIES))
    def test_rate_limit_all_strategies_valid(self, strategy: str) -> None:
        config = RateLimitConfig(name="test", strategy=strategy)
        assert check_node("rate_limit", config) == []


class TestCheckContract:
    """Tests for contract validation (Workstream C)."""

    def test_valid_contract(self) -> None:
        config = ContractConfig(name="create_order", fields="item_id:str")
        assert check_node("contract", config) == []

    def test_contract_bad_name(self) -> None:
        config = ContractConfig(name="Create-Order", fields="x:str")
        errors = check_node("contract", config)
        assert any("snake_case" in e for e in errors)

    def test_contract_bad_direction(self) -> None:
        config = ContractConfig(name="test", direction="up")  # type: ignore[arg-type]
        errors = check_node("contract", config)
        assert any("direction" in e for e in errors)

    def test_contract_empty_fields_without_entity(self) -> None:
        config = ContractConfig(name="test", direction="request", fields="", entity="")
        errors = check_node("contract", config)
        assert any("non-empty" in e for e in errors)

    def test_contract_empty_fields_with_entity_ok(self) -> None:
        config = ContractConfig(
            name="test", direction="request", fields="", entity="order"
        )
        # With entity reference, empty fields are acceptable
        errors = check_node("contract", config)
        assert not any("non-empty" in e for e in errors)

    def test_contract_both_direction_allows_empty_fields(self) -> None:
        config = ContractConfig(name="test", direction="both", fields="")
        errors = check_node("contract", config)
        assert not any("non-empty" in e for e in errors)

    def test_contract_bad_field_type(self) -> None:
        config = ContractConfig(name="test", fields="x:integer")
        errors = check_node("contract", config)
        assert any("unknown type" in e for e in errors)

    @pytest.mark.parametrize("direction", sorted(CONTRACT_DIRECTIONS))
    def test_contract_all_directions_valid(self, direction: str) -> None:
        config = ContractConfig(
            name="test", direction=direction, fields="x:str"  # type: ignore[arg-type]
        )
        assert check_node("contract", config) == []


class TestCheckEdge:
    """Tests for edge validation."""

    def test_valid_feature_flag_edge(self) -> None:
        assert check_edge("route", "feature_flag") == []

    def test_valid_guard_chain_edge(self) -> None:
        assert check_edge("route", "auth") == []
        assert check_edge("route", "role") == []
        assert check_edge("route", "rate_limit") == []
        assert check_edge("role", "auth") == []

    def test_valid_contract_edge(self) -> None:
        assert check_edge("route", "contract") == []

    def test_invalid_edge(self) -> None:
        errors = check_edge("entity", "feature_flag")
        assert len(errors) == 1
        assert "not in ALLOWED_EDGES" in errors[0]


class TestCheckDocument:
    """Tests for full document validation."""

    def test_valid_document(self) -> None:
        doc = {
            "nodes": [
                {
                    "id": "n1",
                    "kind": "feature_flag",
                    "config": FeatureFlagConfig(name="new_checkout"),
                },
                {
                    "id": "n2",
                    "kind": "route",
                    "config": RouteConfig(path="/api/items"),
                },
            ],
            "edges": [
                {"source": "n2", "target": "n1"},
            ],
        }
        assert check_document(doc) == []

    def test_document_with_bad_node(self) -> None:
        doc = {
            "nodes": [
                {
                    "id": "n1",
                    "kind": "feature_flag",
                    "config": FeatureFlagConfig(name="Bad-Name"),
                },
            ],
            "edges": [],
        }
        errors = check_document(doc)
        assert any("snake_case" in e for e in errors)

    def test_document_with_bad_edge(self) -> None:
        doc = {
            "nodes": [
                {"id": "n1", "kind": "entity", "config": EntityConfig()},
                {"id": "n2", "kind": "feature_flag", "config": FeatureFlagConfig()},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
            ],
        }
        errors = check_document(doc)
        assert any("not in ALLOWED_EDGES" in e for e in errors)

    def test_document_with_unknown_source(self) -> None:
        doc = {
            "nodes": [],
            "edges": [{"source": "missing", "target": "also_missing"}],
        }
        errors = check_document(doc)
        assert any("unknown source" in e for e in errors)

    def test_document_with_unknown_target(self) -> None:
        doc = {
            "nodes": [
                {"id": "n1", "kind": "route", "config": RouteConfig()},
            ],
            "edges": [{"source": "n1", "target": "missing"}],
        }
        errors = check_document(doc)
        assert any("unknown target" in e for e in errors)

    def test_unknown_kind(self) -> None:
        doc = {
            "nodes": [
                {"id": "n1", "kind": "unknown_thing", "config": {}},
            ],
            "edges": [],
        }
        errors = check_document(doc)
        assert any("Unknown node kind" in e for e in errors)
