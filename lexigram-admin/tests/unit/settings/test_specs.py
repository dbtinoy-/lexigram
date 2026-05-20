"""Tests for built-in spec registrations and models."""

from __future__ import annotations

import pytest

from lexigram.admin.settings.panel import (
    BrandingSpec,
    CacheSpec,
    ConfigRegistry,
    SecuritySpec,
    register_branding_spec,
    register_cache_spec,
    register_security_spec,
)
from lexigram.admin.settings.panel.nodes import BooleanNode, ColorNode, EnumNode, IntNode, StringNode
from lexigram.admin.settings.panel.registry import MemoryStore


class TestSpecs:
    """Tests for bound built-in specs."""

    def test_branding_spec_nodes(self) -> None:
        nodes = BrandingSpec.get_nodes()
        assert set(nodes) == {"site_name", "primary_color", "logo_url", "favicon_url", "dark_mode"}
        assert isinstance(nodes["site_name"], StringNode)
        assert isinstance(nodes["primary_color"], ColorNode)
        assert isinstance(nodes["dark_mode"], EnumNode)
        assert nodes["dark_mode"].options == ["system", "light", "dark"]
        assert nodes["site_name"].default == "Lexigram Admin"

    def test_cache_spec_nodes(self) -> None:
        nodes = CacheSpec.get_nodes()
        assert set(nodes) == {"enabled", "default_ttl"}
        assert isinstance(nodes["enabled"], BooleanNode)
        assert isinstance(nodes["default_ttl"], IntNode)
        assert nodes["default_ttl"].default == 60

    def test_security_spec_nodes(self) -> None:
        nodes = SecuritySpec.get_nodes()
        assert set(nodes) == {"csp", "hsts_max_age"}
        assert isinstance(nodes["hsts_max_age"], IntNode)
        assert "default-src" in nodes["csp"].default

    def test_unbound_specs_have_no_nodes(self) -> None:
        from lexigram.admin.settings.panel import (
            FeaturesSpec,
            I18nSpec,
            ProfilerSpec,
            RBACSpec,
            RateLimitSpec,
        )

        for spec in (FeaturesSpec, I18nSpec, ProfilerSpec, RBACSpec, RateLimitSpec):
            assert spec.get_nodes() == {}

    def test_register_spec_deduplicates(self) -> None:
        registry = ConfigRegistry()
        register_cache_spec(registry)
        register_cache_spec(registry)
        assert len(registry.get_specs("system")) == 1

    def test_get_specs_filters_specs_without_nodes(self) -> None:
        registry = ConfigRegistry()
        register_branding_spec(registry)
        register_cache_spec(registry)
        register_security_spec(registry)
        namespaces = [s.namespace for s in registry.get_specs("system")]
        assert namespaces == ["admin.branding", "admin.cache", "admin.security"]

    def test_with_defaults_registers_all_bound_specs(self) -> None:
        registry = ConfigRegistry.with_defaults()
        namespaces = {s.namespace for s in registry.get_specs("system")}
        assert namespaces == {"admin.branding", "admin.cache", "admin.security"}
        assert registry.get_spec("admin.cache") is CacheSpec
        assert registry.get_spec("admin.nope") is None

    def test_has_store(self) -> None:
        registry = ConfigRegistry()
        assert registry.has_store("default")
        assert not registry.has_store("db")

    @pytest.mark.asyncio
    async def test_get_values_round_trip_via_store(self) -> None:
        registry = ConfigRegistry()
        register_cache_spec(registry)
        store = MemoryStore()
        registry.register_store("test", store)

        await registry.save_values(
            "admin.cache", {"enabled": "false", "default_ttl": "120"}, store_name="test"
        )
        values = await registry.get_values("admin.cache", store_name="test")
        assert values["enabled"] is False
        assert values["default_ttl"] == 120


class TestRegistryEdgeCases:
    """Edge cases for registry lookups and stores."""

    def test_get_specs_empty_registry(self) -> None:
        registry = ConfigRegistry()
        assert registry.get_specs("system") == []

    async def test_save_values_unknown_namespace_is_noop(self) -> None:
        registry = ConfigRegistry()
        register_cache_spec(registry)
        await registry.save_values("admin.nope", {"x": "1"})

    async def test_get_values_unknown_namespace_is_empty(self) -> None:
        registry = ConfigRegistry()
        register_cache_spec(registry)
        values = await registry.get_values("admin.nope")
        assert values == {}
