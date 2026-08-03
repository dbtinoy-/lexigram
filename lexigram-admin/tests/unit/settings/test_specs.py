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
from lexigram.admin.settings.panel.nodes import (
    BooleanNode,
    ColorNode,
    EnumNode,
    IntNode,
    StringNode,
)
from lexigram.admin.settings.panel.registry import MemoryStore


class TestSpecs:
    """Tests for bound built-in specs."""

    def test_branding_spec_nodes(self) -> None:
        nodes = BrandingSpec.get_nodes()
        assert set(nodes) == {
            "site_name",
            "primary_color",
            "logo_url",
            "favicon_url",
            "dark_mode",
        }
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

    def test_newly_bound_specs_have_real_nodes(self) -> None:
        from lexigram.admin.settings.panel import (
            FeaturesSpec,
            I18nSpec,
            ProfilerSpec,
            RateLimitSpec,
            RBACSpec,
        )

        assert set(FeaturesSpec.get_nodes()) == {
            "activity_feed",
            "api_docs",
            "audit_logging",
            "autosave",
            "command_palette",
            "keyboard_shortcuts",
            "notifications",
            "optimistic_updates",
            "search",
            "theme_toggle",
            "undo_redo",
            "webhooks",
        }
        assert set(I18nSpec.get_nodes()) == {"default_locale", "default_timezone"}
        assert set(ProfilerSpec.get_nodes()) == {"enabled", "slow_threshold_ms"}
        assert set(RBACSpec.get_nodes()) == {"default_role", "allow_anonymous"}
        assert set(RateLimitSpec.get_nodes()) == {
            "burst_size",
            "bulk_per_minute",
            "create_per_minute",
            "delete_per_minute",
            "enabled",
            "requests_per_hour",
            "requests_per_minute",
            "update_per_minute",
        }

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
        assert namespaces == {
            "admin.branding",
            "admin.cache",
            "admin.security",
            "admin.features",
            "admin.i18n",
            "admin.profiler",
            "admin.rate_limit",
            "admin.rbac",
        }
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


class TestPackageSourceGrouping:
    def test_get_package_sources_returns_distinct_sorted_sources(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _SpecA(ConfigSpec):
            namespace = "test.a"
            label = "A"
            icon = "box"
            description = ""
            package_source = "zeta"
            field = StringNode(label="Field")

        class _SpecB(ConfigSpec):
            namespace = "test.b"
            label = "B"
            icon = "box"
            description = ""
            package_source = "alpha"
            field = StringNode(label="Field")

        registry = ConfigRegistry()
        registry.register_spec(_SpecA)
        registry.register_spec(_SpecB)
        assert registry.get_package_sources() == ["alpha", "zeta"]
        assert registry.get_specs_by_package("alpha") == [_SpecB]

    def test_default_package_source_is_built_in(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec

        assert ConfigSpec.package_source == "built-in"


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

    async def test_save_values_skips_readonly_nodes(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _ReadonlySpec(ConfigSpec):
            namespace = "admin.readonly_test"
            label = "Readonly Test"
            icon = "lock"
            description = ""
            locked = StringNode(label="Locked", default="original", readonly=True)

        registry = ConfigRegistry()
        registry._specs["admin.readonly_test"] = _ReadonlySpec
        await registry.save_values("admin.readonly_test", {"locked": "hacked"})
        values = await registry.get_values("admin.readonly_test")
        assert values["locked"] == "original"
