"""Integration tests: contributor route auto-registration via RouteIntegrator."""

from __future__ import annotations

import pytest

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.dashboard.route_integrator import RouteIntegrator
from lexigram.contracts.admin import (
    AdminRouteSpec,
    BaseAdminContributor,
)


class _RouteRecorder:
    def __init__(self) -> None:
        self.routes: list[dict] = []

    def add_route(self, path: str, method: str, handler: object, name: str) -> None:
        self.routes.append({"path": path, "method": method, "handler": handler, "name": name})


class _RouteContributor(BaseAdminContributor):
    name = "api"
    display_name = "API"
    group = "extensions"
    icon = "code"
    priority = 100
    version = "1.0.0"
    package_source = "api"
    required_permissions = frozenset()

    def get_routes(self):
        return [
            AdminRouteSpec(
                path="/admin/api/hello",
                method="GET",
                handler=lambda req: "hello",
                name="hello",
            ),
            AdminRouteSpec(
                path="/admin/api/echo",
                method="POST",
                handler=lambda req: req,
                name="echo",
            ),
        ]


class _EmptyContributor(BaseAdminContributor):
    name = "empty"
    display_name = "Empty"
    group = "test"
    icon = "box"
    priority = 200
    version = "1.0.0"
    package_source = "empty"
    required_permissions = frozenset()


class TestContributorRouteAutoRegistration:
    def test_registers_routes_from_contributor(self) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c = _RouteContributor()
        integrator.register([c])

        assert len(recorder.routes) == 2

    def test_route_paths_and_methods_preserved(self) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c = _RouteContributor()
        integrator.register([c])

        paths = {r["path"] for r in recorder.routes}
        assert "/admin/api/hello" in paths
        assert "/admin/api/echo" in paths

        methods = {r["method"] for r in recorder.routes}
        assert "GET" in methods
        assert "POST" in methods

    def test_route_names_namespaced_by_package(self) -> None:
        naming = NamingPolicy(mode="error")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c = _RouteContributor()
        integrator.register([c])

        names = {r["name"] for r in recorder.routes}
        assert "api.hello" in names
        assert "api.echo" in names

    def test_empty_contributor_registers_no_routes(self) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c = _EmptyContributor()
        integrator.register([c])

        assert len(recorder.routes) == 0

    def test_multiple_contributors_routes_merged(self) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c1 = _RouteContributor()
        c2 = _EmptyContributor()
        integrator.register([c1, c2])

        assert len(recorder.routes) == 2
