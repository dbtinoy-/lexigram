from __future__ import annotations

import logging

import pytest

from lexigram.admin.dashboard.naming_policy import (
    NameCollisionError,
    NamingPolicy,
)
from lexigram.admin.dashboard.page_assembler import PageAssembler
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.dashboard.route_integrator import RouteIntegrator
from lexigram.admin.dashboard.settings_assembler import SettingsPanelAssembler
from lexigram.contracts.admin import (
    AdminRouteSpec,
    BaseAdminContributor,
    ManagementPageDefinition,
    PageCategory,
    SettingsPanelDefinition,
)


class _RouteRecorder:
    def __init__(self) -> None:
        self.routes: list[dict] = []

    def add_route(
        self, path: str, method: str, handler: object, name: str
    ) -> None:
        self.routes.append({"path": path, "method": method, "handler": handler, "name": name})


class TestContributorCollisionModes:
    """End-to-end collision mode behavior across assemblers."""

    def test_two_contributors_different_packages_no_collision(self) -> None:
        naming = NamingPolicy(mode="error")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c1 = _make_contributor("pkg_a", "users")
        c2 = _make_contributor("pkg_b", "users")

        integrator.register([c1, c2])

        assert len(recorder.routes) == 2
        names = [r["name"] for r in recorder.routes]
        assert "pkg_a.users" in names
        assert "pkg_b.users" in names

    def test_same_package_route_name_collision_warns(self, caplog) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c1 = _make_contributor("pkg_a", "users")
        c2 = _make_contributor("pkg_a", "users")  # same pkg, same name → collision after namespacing

        with caplog.at_level(logging.WARNING):
            integrator.register([c1, c2])

        assert any("collision" in r.message.lower() for r in caplog.records)

    def test_same_package_route_name_collision_error_raises(self) -> None:
        naming = NamingPolicy(mode="error")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c1 = _make_contributor("pkg_a", "users")
        c2 = _make_contributor("pkg_a", "users")

        integrator.register([c1])
        with pytest.raises(NameCollisionError):
            integrator.register([c2])

    def test_same_package_settings_panel_collision_error_raises(self) -> None:
        naming = NamingPolicy(mode="error")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c1 = _make_contributor("pkg_a", "settings")
        c2 = _make_contributor("pkg_a", "settings")

        with pytest.raises(NameCollisionError):
            assembler.assemble([c1, c2])

    def test_same_package_page_collision_error_raises(self) -> None:
        naming = NamingPolicy(mode="error")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c1 = _make_contributor("pkg_a", "my_page")
        c2 = _make_contributor("pkg_a", "my_page")

        with pytest.raises(NameCollisionError):
            assembler.assemble([c1, c2])

    def test_different_packages_no_settings_collision(self) -> None:
        naming = NamingPolicy(mode="error")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c1 = _make_contributor("pkg_a", "settings")
        c2 = _make_contributor("pkg_b", "settings")

        panels = assembler.assemble([c1, c2])
        assert len(panels) == 2

    def test_different_packages_no_page_collision(self) -> None:
        naming = NamingPolicy(mode="error")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c1 = _make_contributor("pkg_a", "my_page")
        c2 = _make_contributor("pkg_b", "my_page")

        pages = assembler.assemble([c1, c2])
        assert len(pages) == 2


def _make_contributor(pkg: str, route_name: str) -> BaseAdminContributor:
    """Create a minimal contributor returning one route + one page + one settings panel."""
    class _C(BaseAdminContributor):
        name = pkg
        display_name = pkg.title()
        group = "test"
        icon = "box"
        priority = 100
        version = "0.0.0"
        package_source = pkg
        required_permissions = frozenset()

        def get_routes(self):
            return [
                AdminRouteSpec(
                    path=f"/admin/{pkg}/{route_name}",
                    method="GET",
                    handler=lambda req: f"{pkg}_{route_name}",
                    name=route_name,
                ),
            ]

        def get_management_pages(self):
            return [
                ManagementPageDefinition(
                    name=route_name,
                    title=route_name.title(),
                    contributor=pkg,
                    route_path=f"/admin/{pkg}/{route_name}",
                    handler="fake_module:handler",
                    category=PageCategory.CONFIGURATION,
                ),
            ]

        def get_settings_panels(self):
            return [
                SettingsPanelDefinition(
                    name=route_name,
                    title=route_name.title(),
                    contributor=pkg,
                    route_path=f"/admin/{pkg}/{route_name}",
                    handler="fake_module:handler",
                ),
            ]

    return _C()
