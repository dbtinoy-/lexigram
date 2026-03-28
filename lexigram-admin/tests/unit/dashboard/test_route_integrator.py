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
