from __future__ import annotations

from unittest.mock import ANY, MagicMock

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.route_integrator import RouteIntegrator
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
                handler=lambda req: "hello",
                name="hello",
                permissions=frozenset(),
            ),
            AdminRouteSpec(
                path="/admin/fake/stats",
                method="GET",
                handler=lambda req: "stats",
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

        from lexigram.admin.dashboard.naming_policy import NameCollisionError
        import pytest

        with pytest.raises(NameCollisionError):
            integrator.register([FakeContributor()])
