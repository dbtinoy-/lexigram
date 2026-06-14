"""Tests for ResourceCollector and apply_namespace."""

from __future__ import annotations

import pytest

from lexigram.admin.contributors.resource_collector import ResourceCollector
from lexigram.admin.dashboard.naming_policy import NameCollisionError, NamingPolicy
from lexigram.admin.resources.namespace import apply_namespace
from lexigram.contracts.admin.types import AdminRouteSpec


class _FakeResource:
    name = "users"


class _FakeResourceNoName:
    pass


class _SimpleContributor:
    package_source = "fake_pkg"
    name = "simple"

    def get_resources(self):
        return [_FakeResource]


class _ContributorWithNoName:
    package_source = "other"
    name = "noname"

    def get_resources(self):
        return [_FakeResourceNoName]


class _ContributorSamePkg:
    package_source = "fake_pkg"
    name = "same"

    def get_resources(self):
        return [_FakeResource]


class _ContributorHyphenatedPkg:
    package_source = "lexigram-template"
    name = "hyphen"

    def get_resources(self):
        return [_FakeResource]


class _ContributorWithoutResources:
    package_source = "empty"
    name = "empty"

    def get_resources(self):
        return []


class _ContributorCustomHandler:
    package_source = "handler"
    name = "handler"

    def get_routes(self):
        return [AdminRouteSpec(path="/custom", method="GET", handler=lambda: None, name="custom")]

    def get_resources(self):
        return [_FakeResource]


class TestResourceCollector:
    def test_collects_resources_from_contributor(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_SimpleContributor()])
        assert len(result) == 1
        assert result[0].name == "fake_pkg.users"

    def test_collect_no_resources_returns_empty(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_ContributorWithoutResources()])
        assert result == []

    def test_collect_multiple_contributors(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_SimpleContributor(), _ContributorWithoutResources()])
        assert len(result) == 1

    def test_collision_warn_mode_keeps_first(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_SimpleContributor(), _ContributorSamePkg()])
        assert len(result) == 1

    def test_collision_error_mode_raises(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="error"))
        with pytest.raises(NameCollisionError):
            collector.collect([_SimpleContributor(), _ContributorSamePkg()])

    def test_empty_contributor_list(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([])
        assert result == []

    def test_resource_without_explicit_name_uses_class_name(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_ContributorWithNoName()])
        assert len(result) == 1
        assert "other" in result[0].name

    def test_contributor_with_get_resources(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_ContributorCustomHandler()])
        assert len(result) == 1
        assert result[0].name == "handler.users"

    def test_hyphenated_package_source_collects(self) -> None:
        collector = ResourceCollector(NamingPolicy(mode="warn"))
        result = collector.collect([_ContributorHyphenatedPkg()])
        assert len(result) == 1
        assert result[0].name == "lexigram_template.users"


class TestApplyNamespace:
    def test_creates_subclass_with_namespaced_name(self) -> None:
        class OriginalResource:
            name = "users"

        wrapped = apply_namespace(OriginalResource, "fake_pkg.users")
        assert wrapped.name == "fake_pkg.users"
        assert issubclass(wrapped, OriginalResource)

    def test_hyphenated_package_source_is_sanitized(self) -> None:
        class OriginalResource:
            name = "users"

        wrapped = apply_namespace(OriginalResource, "lexigram-template.users")
        assert wrapped.name == "lexigram_template.users"
        assert wrapped.route_prefix == "/lexigram_template/users"

    def test_route_prefix_from_dotted_name(self) -> None:
        class OriginalResource:
            name = "users"

        wrapped = apply_namespace(OriginalResource, "pkg.users")
        assert wrapped.route_prefix == "/pkg/users"

    def test_nested_namespace(self) -> None:
        class OriginalResource:
            name = "deep"

        wrapped = apply_namespace(OriginalResource, "my_pkg.deep.thing")
        assert wrapped.name == "my_pkg.deep.thing"
        assert wrapped.route_prefix == "/my_pkg/deep.thing"

    def test_preserves_class_attributes(self) -> None:
        class OriginalResource:
            name = "original"
            label = "Original"
            icon = "star"

        wrapped = apply_namespace(OriginalResource, "pkg.original")
        assert wrapped.label == "Original"
        assert wrapped.icon == "star"

    def test_idempotent(self) -> None:
        class OriginalResource:
            name = "x"

        a = apply_namespace(OriginalResource, "pkg.x")
        b = apply_namespace(OriginalResource, "pkg.x")
        assert a is b
