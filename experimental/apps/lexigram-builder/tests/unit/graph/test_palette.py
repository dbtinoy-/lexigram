"""Tests for the palette module."""

from __future__ import annotations

import pytest

from lexigram_builder.graph.palette import (
    ALLOWED_EDGES,
    EDGE_KIND_MAP,
    KIND_AUTH,
    KIND_CONTRACT,
    KIND_ENTITY,
    KIND_FEATURE_FLAG,
    KIND_JOB,
    KIND_MIDDLEWARE,
    KIND_RATE_LIMIT,
    KIND_ROLE,
    KIND_ROUTE,
    KIND_ROUTE_GROUP,
    KIND_SERVICE,
    KNOWN_KINDS,
    NODE_COLORS,
    NODE_DEFAULTS,
    NODE_PORTS,
    PALETTE_CATEGORIES,
    PORT_COMPATIBILITY,
    PORT_TYPES,
)


class TestKnownKinds:
    """Tests for KNOWN_KINDS."""

    def test_all_expected_kinds_present(self) -> None:
        expected = {
            "route", "route_group", "entity", "service", "job",
            "middleware", "feature_flag", "auth", "role", "rate_limit",
            "contract",
        }
        assert KNOWN_KINDS == expected

    def test_kind_constants_match_strings(self) -> None:
        assert KIND_ROUTE == "route"
        assert KIND_FEATURE_FLAG == "feature_flag"
        assert KIND_AUTH == "auth"
        assert KIND_ROLE == "role"
        assert KIND_RATE_LIMIT == "rate_limit"
        assert KIND_CONTRACT == "contract"


class TestNodePorts:
    """Tests for NODE_PORTS."""

    def test_all_kinds_have_ports(self) -> None:
        for kind in KNOWN_KINDS:
            assert kind in NODE_PORTS, f"{kind} missing from NODE_PORTS"

    def test_ports_are_tuple_of_two_lists(self) -> None:
        for kind, (inputs, outputs) in NODE_PORTS.items():
            assert isinstance(inputs, list), f"{kind} inputs should be list"
            assert isinstance(outputs, list), f"{kind} outputs should be list"


class TestAllowedEdges:
    """Tests for ALLOWED_EDGES."""

    def test_feature_flag_edges_exist(self) -> None:
        assert (KIND_ROUTE, KIND_FEATURE_FLAG) in ALLOWED_EDGES
        assert (KIND_ROUTE_GROUP, KIND_FEATURE_FLAG) in ALLOWED_EDGES

    def test_guard_chain_edges_exist(self) -> None:
        assert (KIND_ROUTE, KIND_AUTH) in ALLOWED_EDGES
        assert (KIND_ROUTE, KIND_ROLE) in ALLOWED_EDGES
        assert (KIND_ROUTE, KIND_RATE_LIMIT) in ALLOWED_EDGES
        assert (KIND_ROLE, KIND_AUTH) in ALLOWED_EDGES

    def test_contract_edges_exist(self) -> None:
        assert (KIND_ROUTE, KIND_CONTRACT) in ALLOWED_EDGES
        assert (KIND_CONTRACT, KIND_ENTITY) in ALLOWED_EDGES

    def test_edge_kind_map_covers_all_allowed_edges(self) -> None:
        for edge in ALLOWED_EDGES:
            assert edge in EDGE_KIND_MAP, f"{edge} missing from EDGE_KIND_MAP"


class TestNodeDefaults:
    """Tests for NODE_DEFAULTS."""

    def test_all_kinds_have_defaults(self) -> None:
        for kind in KNOWN_KINDS:
            assert kind in NODE_DEFAULTS, f"{kind} missing from NODE_DEFAULTS"

    def test_feature_flag_defaults(self) -> None:
        defaults = NODE_DEFAULTS[KIND_FEATURE_FLAG]
        assert defaults["name"] == "new_checkout"
        assert defaults["enabled"] is True
        assert defaults["description"] == ""

    def test_auth_defaults(self) -> None:
        defaults = NODE_DEFAULTS[KIND_AUTH]
        assert defaults["name"] == "jwt_auth"
        assert defaults["provider"] == "jwt"

    def test_role_defaults(self) -> None:
        defaults = NODE_DEFAULTS[KIND_ROLE]
        assert defaults["name"] == "admin"
        assert defaults["permissions"] == []

    def test_rate_limit_defaults(self) -> None:
        defaults = NODE_DEFAULTS[KIND_RATE_LIMIT]
        assert defaults["name"] == "api_rate_limit"
        assert defaults["strategy"] == "sliding_window"
        assert defaults["max_requests"] == 100
        assert defaults["window_seconds"] == 60

    def test_contract_defaults(self) -> None:
        defaults = NODE_DEFAULTS[KIND_CONTRACT]
        assert defaults["name"] == "create_order"
        assert defaults["direction"] == "request"
        assert defaults["fields"] == "item_id:str, quantity:int"


class TestNodeColors:
    """Tests for NODE_COLORS."""

    def test_all_kinds_have_colors(self) -> None:
        for kind in KNOWN_KINDS:
            assert kind in NODE_COLORS, f"{kind} missing from NODE_COLORS"


class TestPaletteCategories:
    """Tests for PALETTE_CATEGORIES."""

    def test_expected_categories_present(self) -> None:
        assert "Core" in PALETTE_CATEGORIES
        assert "Features" in PALETTE_CATEGORIES
        assert "Security & Policy" in PALETTE_CATEGORIES
        assert "Data" in PALETTE_CATEGORIES

    def test_feature_flag_in_features_category(self) -> None:
        assert KIND_FEATURE_FLAG in PALETTE_CATEGORIES["Features"]

    def test_guard_nodes_in_security_category(self) -> None:
        assert KIND_AUTH in PALETTE_CATEGORIES["Security & Policy"]
        assert KIND_ROLE in PALETTE_CATEGORIES["Security & Policy"]
        assert KIND_RATE_LIMIT in PALETTE_CATEGORIES["Security & Policy"]

    def test_contract_in_data_category(self) -> None:
        assert KIND_CONTRACT in PALETTE_CATEGORIES["Data"]


class TestPortTypes:
    """Tests for PORT_TYPES and PORT_COMPATIBILITY."""

    def test_port_types_defined(self) -> None:
        assert "config_ref" in PORT_TYPES
        assert "entity_ref" in PORT_TYPES
        assert "data_flow" in PORT_TYPES

    def test_port_compatibility_self_referential(self) -> None:
        for port_type, compatible in PORT_COMPATIBILITY.items():
            assert port_type in compatible
