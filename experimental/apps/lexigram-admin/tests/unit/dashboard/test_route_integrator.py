from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.route_integrator import (
    RouteIntegrator,
    _resolve_primary_color,
)
from lexigram.contracts.admin import AdminRouteSpec, BaseAdminContributor


class FakeContributor(BaseAdminContributor):
    name = "fake"
    display_name = "Fake"
    group = "test"
    icon = "box"
    priority = 100
    version = "0.0.0"
    package_source = "fake_pkg"
    required_permissions = frozenset()

    def get_routes(self):
        return [
            AdminRouteSpec(
                path="/admin/fake/hello",
                method="GET",
                handler=lambda _req: "hello",
                name="hello",
                permissions=frozenset(),
            ),
            AdminRouteSpec(
                path="/admin/fake/stats",
                method="GET",
                handler=lambda _req: "stats",
                name="stats",
                permissions=frozenset({"admin.view"}),
            ),
        ]


class TestRouteIntegrator:
    def test_registers_each_route_on_router(self) -> None:
        router = MagicMock()
        naming = NamingPolicy(mode="warn")
        integrator = RouteIntegrator(router=router, naming_policy=naming)

        integrator.register([FakeContributor()])

        assert router.add_route.call_count == 2
        router.add_route.assert_any_call(
            path="/admin/fake/hello",
            method="GET",
            handler=ANY,
            name="fake_pkg.hello",
        )
        router.add_route.assert_any_call(
            path="/admin/fake/stats",
            method="GET",
            handler=ANY,
            name="fake_pkg.stats",
        )

    def test_strips_mount_prefix_from_route_specs(self) -> None:
        router = MagicMock()
        naming = NamingPolicy(mode="warn")
        integrator = RouteIntegrator(
            router=router, naming_policy=naming, route_prefix="/admin"
        )

        integrator.register([FakeContributor()])

        router.add_route.assert_any_call(
            path="/fake/hello",
            method="GET",
            handler=ANY,
            name="fake_pkg.hello",
        )
        router.add_route.assert_any_call(
            path="/fake/stats",
            method="GET",
            handler=ANY,
            name="fake_pkg.stats",
        )

    def test_namespaces_route_names(self) -> None:
        router = MagicMock()
        naming = NamingPolicy(mode="warn")
        integrator = RouteIntegrator(router=router, naming_policy=naming)

        integrator.register([FakeContributor()])

        calls = router.add_route.call_args_list
        names = [call.kwargs["name"] for call in calls]
        assert names == ["fake_pkg.hello", "fake_pkg.stats"]

    def test_collision_warn_does_not_raise(self) -> None:
        router = MagicMock()
        naming = NamingPolicy(mode="warn")
        integrator = RouteIntegrator(router=router, naming_policy=naming)

        integrator.register([FakeContributor(), FakeContributor()])

        assert router.add_route.call_count >= 2

    def test_collision_error_raises(self) -> None:
        router = MagicMock()
        naming = NamingPolicy(mode="error")
        integrator = RouteIntegrator(router=router, naming_policy=naming)

        integrator.register([FakeContributor()])

        import pytest

        from lexigram.admin.dashboard.naming_policy import NameCollisionError

        with pytest.raises(NameCollisionError):
            integrator.register([FakeContributor()])


class TestClusterAliases:
    def _integrator(self, router: object) -> RouteIntegrator:
        return RouteIntegrator(
            router=router,  # type: ignore[arg-type]
            naming_policy=NamingPolicy(mode="warn"),
            route_prefix="/admin",
        )

    def test_real_page_route_is_aliased_under_cluster_namespace(self) -> None:
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.admin.navigation.clusters import CLUSTER_GROUP
        from lexigram.contracts.admin import (
            ManagementPageDefinition,
            NavigationContribution,
        )

        router = AdminRouter(config=MagicMock())
        handler = MagicMock(return_value="page")

        class ClusterContributor(FakeContributor):
            name = "cluster"
            package_source = "cluster_pkg"

            def get_navigation_items(self):
                return [
                    NavigationContribution(
                        label="Web",
                        url="/admin/web",
                        icon="globe",
                        group=CLUSTER_GROUP,
                    ),
                ]

            def get_management_pages(self):
                return [
                    ManagementPageDefinition(
                        name="web_overview",
                        title="Web",
                        contributor="web",
                        route_path="/web",
                        handler=handler,
                    ),
                ]

        self._integrator(router).register([ClusterContributor()])

        paths = [r.path for r in router._extra_routes]
        assert "/infrastructure/web" in paths
        source = next(r for r in router._extra_routes if r.path == "/web")
        alias = next(r for r in router._extra_routes if r.path == "/infrastructure/web")
        assert alias.endpoint is source.endpoint
        assert alias.name == "cluster_alias_web"
        from lexigram.admin.dashboard.route_integrator import StructuredPageHandler

        assert isinstance(source.endpoint, StructuredPageHandler)
        assert source.endpoint._handler is handler

    def test_placeholder_route_is_aliased_under_cluster_namespace(self) -> None:
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.admin.navigation.clusters import CLUSTER_GROUP
        from lexigram.contracts.admin import NavigationContribution

        router = AdminRouter(config=MagicMock())

        class NavOnlyContributor(FakeContributor):
            name = "cluster"
            package_source = "cluster_pkg"

            def get_navigation_items(self):
                return [
                    NavigationContribution(
                        label="Cache",
                        url="/admin/cache",
                        icon="zap",
                        group=CLUSTER_GROUP,
                    ),
                ]

        self._integrator(router).register([NavOnlyContributor()])

        paths = [r.path for r in router._extra_routes]
        assert "/cache" in paths
        assert "/infrastructure/cache" in paths
        source = next(r for r in router._extra_routes if r.path == "/cache")
        alias = next(
            r for r in router._extra_routes if r.path == "/infrastructure/cache"
        )
        assert alias.endpoint == source.endpoint

    def test_non_cluster_nav_items_get_no_alias(self) -> None:
        from lexigram.admin.core.routing import AdminRouter
        from lexigram.contracts.admin import NavigationContribution

        router = AdminRouter(config=MagicMock())

        class FrameworkContributor(FakeContributor):
            name = "framework"
            package_source = "framework_pkg"

            def get_navigation_items(self):
                return [
                    NavigationContribution(
                        label="Auth",
                        url="/admin/auth",
                        icon="lock",
                    ),
                ]

        self._integrator(router).register([FrameworkContributor()])

        paths = [r.path for r in router._extra_routes]
        assert "/infrastructure/auth" not in paths


class TestResolvePrimaryColor:
    @pytest.mark.asyncio
    async def test_returns_saved_branding_color(self) -> None:
        registry = MagicMock()
        registry.get_values = AsyncMock(return_value={"primary_color": "#123456"})
        container = MagicMock()
        container.resolve = AsyncMock(return_value=registry)

        color = await _resolve_primary_color(container)

        assert color == "#123456"

    @pytest.mark.asyncio
    async def test_falls_back_when_registry_unavailable(self) -> None:
        class _BrokenResolver:
            async def resolve(self, *args: object, **kwargs: object) -> object:
                raise RuntimeError("no registry")

        color = await _resolve_primary_color(_BrokenResolver())

        assert color == "#6b7280"
