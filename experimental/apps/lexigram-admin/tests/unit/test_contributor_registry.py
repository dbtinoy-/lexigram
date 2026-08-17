"""Tests for ContributorRegistry."""
from __future__ import annotations

from lexigram.admin.contributors.registry import ContributorRegistry
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol


class StubContributor:
    def __init__(self, name="stub", group="framework", priority=50):
        self._name = name
        self._group = group
        self._priority = priority

    @property
    def name(self): return self._name

    @property
    def display_name(self): return self._name.title()

    @property
    def group(self): return self._group

    @property
    def icon(self): return "box"

    @property
    def priority(self): return self._priority

    def get_dashboard_widgets(self): return []
    def get_navigation_items(self): return []
    def get_management_pages(self): return []
    def get_settings_panels(self): return []
    def get_health_definitions(self): return []
    def get_actions(self): return []
    async def on_admin_boot(self, container): pass
    async def on_admin_shutdown(self): pass


class TestContributorRegistry:
    def test_implements_protocol(self) -> None:
        registry = ContributorRegistry()
        assert isinstance(registry, AdminContributorRegistryProtocol)

    def test_register_and_get(self) -> None:
        registry = ContributorRegistry()
        contributor = StubContributor(name="cache")
        registry.register(contributor)
        assert registry.get("cache") is contributor

    def test_get_nonexistent_returns_none(self) -> None:
        registry = ContributorRegistry()
        assert registry.get("nonexistent") is None

    def test_get_all_sorted_by_priority(self) -> None:
        registry = ContributorRegistry()
        registry.register(StubContributor(name="low", priority=100))
        registry.register(StubContributor(name="high", priority=10))
        registry.register(StubContributor(name="mid", priority=50))

        all_contribs = registry.get_all()
        names = [c.name for c in all_contribs]
        assert names == ["high", "mid", "low"]

    def test_get_by_group(self) -> None:
        registry = ContributorRegistry()
        registry.register(StubContributor(name="a", group="infra"))
        registry.register(StubContributor(name="b", group="security"))
        registry.register(StubContributor(name="c", group="infra"))

        infra = registry.get_by_group("infra")
        names = [c.name for c in infra]
        assert sorted(names) == ["a", "c"]

    def test_get_by_group_empty(self) -> None:
        registry = ContributorRegistry()
        assert registry.get_by_group("nonexistent") == []

    def test_with_defaults_creates_empty(self) -> None:
        registry = ContributorRegistry.with_defaults()
        assert isinstance(registry, ContributorRegistry)

    def test_duplicate_register_overwrites(self) -> None:
        registry = ContributorRegistry()
        c1 = StubContributor(name="cache", priority=10)
        c2 = StubContributor(name="cache", priority=20)
        registry.register(c1)
        registry.register(c2)
        assert registry.get("cache") is c2
        assert len(registry.get_all()) == 1
