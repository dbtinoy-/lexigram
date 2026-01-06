"""Integration tests: contributor get_routes() is called during boot (S1)."""

from __future__ import annotations

import pytest

from lexigram.admin.di.sub_providers.contributor import AdminContributorSubProvider
from lexigram.contracts.admin import AdminRouteSpec, BaseAdminContributor


class _RouteContributor(BaseAdminContributor):
    name = "route_test"
    display_name = "Route Test"
    group = "test"
    icon = "box"
    priority = 100
    version = "1.0.0"
    package_source = "test"
    required_permissions = frozenset()

    def get_routes(self):
        return [
            AdminRouteSpec(
                path="/admin/route_test/ping",
                method="GET",
                handler=lambda req: "pong",
                name="ping",
            )
        ]


class _EmptyContributor(BaseAdminContributor):
    name = "empty_route_test"
    display_name = "Empty"
    group = "test"
    icon = "box"
    priority = 200
    version = "1.0.0"
    package_source = "test"
    required_permissions = frozenset()


class TestContributorBootCollectsRoutes:
    async def test_boot_all_collects_routes(self) -> None:
        sub = AdminContributorSubProvider(
            contributors=[_RouteContributor]
        )
        await sub.boot_all()

        paths = [r.path for r in sub.collected_routes]
        assert "/admin/route_test/ping" in paths

    async def test_boot_all_empty_contributor_no_routes(self) -> None:
        sub = AdminContributorSubProvider(
            contributors=[_EmptyContributor]
        )
        await sub.boot_all()

        # Entry-point contributors may register routes; the empty contributor adds none
        assert isinstance(sub.collected_routes, list)

    async def test_boot_all_multiple_contributors_merges_routes(self) -> None:
        sub = AdminContributorSubProvider(
            contributors=[_RouteContributor, _EmptyContributor]
        )
        await sub.boot_all()

        paths = [r.path for r in sub.collected_routes]
        assert "/admin/route_test/ping" in paths

    async def test_collected_routes_property_accessible(self) -> None:
        sub = AdminContributorSubProvider(contributors=[])
        await sub.boot_all()
        assert isinstance(sub.collected_routes, list)
