"""Integration tests: first-party contributors with no resources.

Verifies the system handles contributors gracefully when they don't
define get_resources() — relying on the base class default (empty list).
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.contributors.resource_collector import ResourceCollector
from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.contracts.admin import BaseAdminContributor


class _ContributorNoOverride(BaseAdminContributor):
    name = "no_resources"
    display_name = "No Resources"
    group = "test"
    icon = "box"
    priority = 100
    version = "1.0.0"
    package_source = "no_res"
    required_permissions: frozenset[str] | dict[str, Any] = frozenset()


class TestFirstPartyContributorNoResources:
    def test_inherits_empty_get_resources(self) -> None:
        c = _ContributorNoOverride()
        resources = c.get_resources()
        assert len(resources) == 0

    def test_resource_collector_handles_no_resource_contributor(self) -> None:
        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c = _ContributorNoOverride()
        resources = collector.collect([c])
        assert len(resources) == 0

    def test_mixed_contributors_with_and_without_resources(self) -> None:
        class _HasResource(BaseAdminContributor):
            name = "has_res"
            display_name = "Has Resources"
            group = "test"
            icon = "box"
            priority = 100
            version = "1.0.0"
            package_source = "has_res"
            required_permissions: frozenset[str] | dict[str, Any] = frozenset()

            def get_resources(self):
                class _Res:
                    name = "item"
                return [_Res]

        naming = NamingPolicy(mode="warn")
        collector = ResourceCollector(naming_policy=naming)

        c1 = _ContributorNoOverride()
        c2 = _HasResource()
        resources = collector.collect([c1, c2])

        assert len(resources) == 1
        assert resources[0].name == "has_res.item"
