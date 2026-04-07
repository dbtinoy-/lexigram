"""Integration tests: contributor resource contribution end-to-end."""

from __future__ import annotations

import pytest

from lexigram.admin.contributors.resource_collector import ResourceCollector
from lexigram.admin.dashboard.naming_policy import NameCollisionError, NamingPolicy
from lexigram.admin.resources.namespace import apply_namespace
from lexigram.contracts.admin import (
    BaseAdminContributor,
)


class _FakeJobResource:
    name = "jobs"


class _FakeLogResource:
    name = "logs"


class _FakePluginContributor(BaseAdminContributor):
    name = "fake_pkg"
    display_name = "Fake Plugin"
    group = "test"
    icon = "box"
    priority = 200
    version = "1.0.0"
    package_source = "fake_pkg"
    required_permissions = frozenset()

    def get_resources(self):
        return [_FakeJobResource, _FakeLogResource]


class _EmptyContributor(BaseAdminContributor):
    name = "empty"
    display_name = "Empty"
    group = "test"
    icon = "box"
    priority = 100
    version = "1.0.0"
    package_source = "empty"
    required_permissions = frozenset()


class TestContributorResourceEndToEnd:
    def test_resources_collected_from_contributor(self) -> None:
        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c = _FakePluginContributor()
        resources = collector.collect([c])

        assert len(resources) == 2

    def test_resources_namespaced_by_package_source(self) -> None:
        naming = NamingPolicy(mode="error")
        collector = ResourceCollector(naming_policy=naming)

        c = _FakePluginContributor()
        resources = collector.collect([c])

        names = sorted(r.name for r in resources)
        assert names == ["fake_pkg.jobs", "fake_pkg.logs"]

    def test_empty_contributor_yields_no_resources(self) -> None:
        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c = _EmptyContributor()
        resources = collector.collect([c])

        assert len(resources) == 0

    def test_route_prefix_derived_from_namespace(self) -> None:
        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c = _FakePluginContributor()
        resources = collector.collect([c])

        job_resource = next(r for r in resources if r.name == "fake_pkg.jobs")
        assert job_resource.route_prefix == "/fake_pkg/jobs"

    def test_collision_between_two_packages_warn_mode_keeps_first(self) -> None:
        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c1 = _FakePluginContributor()
        c2 = _FakePluginContributor()

        resources = collector.collect([c1, c2])

        assert len(resources) == 2

    def test_collision_same_package_error_mode_raises(self) -> None:
        class _SamePkgContributor(BaseAdminContributor):
            name = "fake_pkg"
            display_name = "Fake Plugin"
            group = "test"
            icon = "box"
            priority = 200
            version = "1.0.0"
            package_source = "fake_pkg"
            required_permissions = frozenset()

            def get_resources(self):
                return [_FakeJobResource, _FakeJobResource]

        naming = NamingPolicy(mode="error")
        collector = ResourceCollector(naming_policy=naming)

        with pytest.raises(NameCollisionError):
            collector.collect([_SamePkgContributor()])

    def test_apply_namespace_creates_subclass_with_namespaced_name(self) -> None:
        wrapped = apply_namespace(_FakeJobResource, "fake_pkg.jobs")
        assert wrapped.name == "fake_pkg.jobs"
        assert issubclass(wrapped, _FakeJobResource)

    def test_apply_namespace_derives_route_prefix(self) -> None:
        wrapped = apply_namespace(_FakeJobResource, "fake_pkg.jobs")
        assert wrapped.route_prefix == "/fake_pkg/jobs"

    def test_apply_namespace_is_idempotent(self) -> None:
        a = apply_namespace(_FakeJobResource, "fake_pkg.jobs")
        b = apply_namespace(_FakeJobResource, "fake_pkg.jobs")
        assert a is b

    def test_multiple_contributors_resources_merged(self) -> None:
        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c1 = _FakePluginContributor()
        c2 = _EmptyContributor()

        resources = collector.collect([c1, c2])
        assert len(resources) == 2
