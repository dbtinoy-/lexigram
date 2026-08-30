"""Tests for the parsing module — round-trip serialization."""

from __future__ import annotations

import pytest

from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    FeatureFlagConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
)
from lexigram_builder.graph.parsing import (
    config_to_dict,
    document_to_dict,
    parse_document,
    parse_node_config,
)
from lexigram_builder.graph.palette import (
    KIND_AUTH,
    KIND_CONTRACT,
    KIND_FEATURE_FLAG,
    KIND_RATE_LIMIT,
    KIND_ROLE,
    KIND_ROUTE,
)


class TestParseNodeConfig:
    """Tests for parse_node_config."""

    def test_parse_feature_flag(self) -> None:
        raw = {"name": "new_checkout", "enabled": True, "description": "Test"}
        config = parse_node_config(KIND_FEATURE_FLAG, raw)
        assert isinstance(config, FeatureFlagConfig)
        assert config.name == "new_checkout"
        assert config.enabled is True
        assert config.description == "Test"

    def test_parse_feature_flag_defaults(self) -> None:
        config = parse_node_config(KIND_FEATURE_FLAG, {})
        assert config.name == "new_checkout"
        assert config.enabled is True

    def test_parse_auth(self) -> None:
        raw = {"name": "jwt_auth", "provider": "jwt"}
        config = parse_node_config(KIND_AUTH, raw)
        assert isinstance(config, AuthConfig)
        assert config.name == "jwt_auth"
        assert config.provider == "jwt"

    def test_parse_role(self) -> None:
        raw = {"name": "admin", "permissions": ["read", "write"], "inherits": "user"}
        config = parse_node_config(KIND_ROLE, raw)
        assert isinstance(config, RoleConfig)
        assert config.name == "admin"
        assert config.permissions == ("read", "write")
        assert config.inherits == "user"

    def test_parse_role_permissions_as_string(self) -> None:
        raw = {"name": "admin", "permissions": "read,write"}
        config = parse_node_config(KIND_ROLE, raw)
        assert config.permissions == ("read", "write")

    def test_parse_rate_limit(self) -> None:
        raw = {
            "name": "api_limit",
            "strategy": "fixed_window",
            "max_requests": 50,
            "window_seconds": 30,
        }
        config = parse_node_config(KIND_RATE_LIMIT, raw)
        assert isinstance(config, RateLimitConfig)
        assert config.name == "api_limit"
        assert config.strategy == "fixed_window"
        assert config.max_requests == 50
        assert config.window_seconds == 30

    def test_parse_contract(self) -> None:
        raw = {
            "name": "create_order",
            "direction": "request",
            "fields": "item_id:str, quantity:int",
            "entity": "order",
            "enabled": True,
            "description": "Order creation contract",
        }
        config = parse_node_config(KIND_CONTRACT, raw)
        assert isinstance(config, ContractConfig)
        assert config.name == "create_order"
        assert config.direction == "request"
        assert config.entity == "order"

    def test_parse_route(self) -> None:
        raw = {"path": "/api/items", "ops": ["create", "get"]}
        config = parse_node_config(KIND_ROUTE, raw)
        assert isinstance(config, RouteConfig)
        assert config.path == "/api/items"
        assert config.ops == ("create", "get")

    def test_parse_unknown_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown node kind"):
            parse_node_config("unknown_kind", {})


class TestConfigToDict:
    """Tests for config_to_dict."""

    def test_feature_flag_to_dict(self) -> None:
        config = FeatureFlagConfig(name="test", enabled=False, description="desc")
        result = config_to_dict(KIND_FEATURE_FLAG, config)
        assert result == {
            "name": "test",
            "enabled": False,
            "description": "desc",
        }

    def test_auth_to_dict(self) -> None:
        config = AuthConfig(name="test", provider="api_key")
        result = config_to_dict(KIND_AUTH, config)
        assert result == {"name": "test", "provider": "api_key"}

    def test_role_to_dict(self) -> None:
        config = RoleConfig(name="test", permissions=("read",), inherits="base")
        result = config_to_dict(KIND_ROLE, config)
        assert result == {
            "name": "test",
            "permissions": ["read"],
            "inherits": "base",
        }

    def test_rate_limit_to_dict(self) -> None:
        config = RateLimitConfig(
            name="test", strategy="token_bucket",
            max_requests=10, window_seconds=5,
        )
        result = config_to_dict(KIND_RATE_LIMIT, config)
        assert result == {
            "name": "test",
            "strategy": "token_bucket",
            "max_requests": 10,
            "window_seconds": 5,
        }

    def test_contract_to_dict(self) -> None:
        config = ContractConfig(
            name="test", direction="both", fields="x:int",
            entity="item", enabled=False, description="d",
        )
        result = config_to_dict(KIND_CONTRACT, config)
        assert result == {
            "name": "test",
            "direction": "both",
            "fields": "x:int",
            "entity": "item",
            "enabled": False,
            "description": "d",
        }

    def test_unknown_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown node kind"):
            config_to_dict("unknown", None)


class TestRoundTrip:
    """Tests for parse → serialize round-trip fidelity."""

    def _round_trip(self, kind: str, raw: dict) -> dict:
        """Parse a raw config dict and serialize it back."""
        config = parse_node_config(kind, raw)
        return config_to_dict(kind, config)

    def test_feature_flag_round_trip(self) -> None:
        raw = {"name": "test", "enabled": False, "description": "desc"}
        assert self._round_trip(KIND_FEATURE_FLAG, raw) == raw

    def test_auth_round_trip(self) -> None:
        raw = {"name": "test", "provider": "oauth2"}
        assert self._round_trip(KIND_AUTH, raw) == raw

    def test_role_round_trip(self) -> None:
        raw = {"name": "test", "permissions": ["read"], "inherits": "base"}
        result = self._round_trip(KIND_ROLE, raw)
        assert result["name"] == "test"
        assert result["permissions"] == ["read"]
        assert result["inherits"] == "base"

    def test_rate_limit_round_trip(self) -> None:
        raw = {
            "name": "test",
            "strategy": "sliding_window",
            "max_requests": 100,
            "window_seconds": 60,
        }
        assert self._round_trip(KIND_RATE_LIMIT, raw) == raw

    def test_contract_round_trip(self) -> None:
        raw = {
            "name": "test",
            "direction": "request",
            "fields": "x:int",
            "entity": "",
            "enabled": True,
            "description": "",
        }
        assert self._round_trip(KIND_CONTRACT, raw) == raw


class TestDocumentRoundTrip:
    """Tests for full document parse/serialize round-trip."""

    def test_document_round_trip(self) -> None:
        raw_doc = {
            "nodes": [
                {
                    "id": "n1",
                    "kind": "feature_flag",
                    "config": {"name": "new_checkout", "enabled": True, "description": ""},
                },
                {
                    "id": "n2",
                    "kind": "auth",
                    "config": {"name": "jwt_auth", "provider": "jwt"},
                },
                {
                    "id": "n3",
                    "kind": "role",
                    "config": {"name": "admin", "permissions": ["read"], "inherits": ""},
                },
            ],
            "edges": [
                {"source": "n1", "target": "n2", "kind": "route_to_auth"},
            ],
        }

        parsed = parse_document(raw_doc)
        assert len(parsed["nodes"]) == 3
        assert isinstance(parsed["nodes"][0]["config"], FeatureFlagConfig)
        assert isinstance(parsed["nodes"][1]["config"], AuthConfig)
        assert isinstance(parsed["nodes"][2]["config"], RoleConfig)

        serialized = document_to_dict(parsed)
        assert serialized == raw_doc

    def test_empty_document(self) -> None:
        raw = {"nodes": [], "edges": []}
        parsed = parse_document(raw)
        assert parsed == {"nodes": [], "edges": []}
        assert document_to_dict(parsed) == raw
