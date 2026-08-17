"""Integration tests: contributor management page assembly end-to-end."""

from __future__ import annotations

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.page_assembler import PageAssembler
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.dashboard.route_integrator import RouteIntegrator
from lexigram.admin.types import AdminUser
from lexigram.contracts.admin import (
    BaseAdminContributor,
    ManagementPageDefinition,
    PageCategory,
)


class _RouteRecorder:
    def __init__(self) -> None:
        self.routes: list[dict] = []

    def add_route(self, path: str, method: str, handler: object, name: str) -> None:
        self.routes.append({"path": path, "method": method, "handler": handler, "name": name})


class _PageContributor(BaseAdminContributor):
    name = "demo"
    display_name = "Demo"
    group = "content"
    icon = "file-text"
    priority = 100
    version = "1.0.0"
    package_source = "demo"
    required_permissions = frozenset()

    def get_management_pages(self):
        return [
            ManagementPageDefinition(
                name="users",
                title="Users",
                contributor="demo",
                route_path="/admin/demo/users",
                handler=lambda req: "users page",
                category=PageCategory.CONFIGURATION,
                permission="demo.view",
            ),
        ]


class _PublicPageContributor(BaseAdminContributor):
    name = "public"
    display_name = "Public"
    group = "content"
    icon = "globe"
    priority = 100
    version = "1.0.0"
    package_source = "public"
    required_permissions = frozenset()

    def get_management_pages(self):
        return [
            ManagementPageDefinition(
                name="about",
                title="About",
                contributor="public",
                route_path="/admin/public/about",
                handler=lambda req: "about page",
                category=PageCategory.INFRASTRUCTURE,
                permission=None,
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


class TestContributorPageEndToEnd:
    def test_pages_assembled_and_routes_registered(self) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c = _PageContributor()
        integrator.register([c])

        page_names = [r["name"] for r in recorder.routes if "demo" in r["name"]]
        assert any("demo.users" in name for name in page_names)

    def test_page_namespaced_by_package_source(self) -> None:
        naming = NamingPolicy(mode="error")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c = _PublicPageContributor()
        pages = assembler.assemble([c])

        assert len(pages) == 1
        assert pages[0].name == "public.about"

    def test_empty_contributor_yields_no_pages(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c = _EmptyContributor()
        pages = assembler.assemble([c])

        assert len(pages) == 0

    def test_page_permission_filter_removes_restricted(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c = _PageContributor()
        user = AdminUser(id="1", username="test", email="test@test.com", permissions=[])
        pages = assembler.assemble([c], user=user)

        assert len(pages) == 0

    def test_page_visible_to_user_with_permission(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c = _PageContributor()
        user = AdminUser(id="1", username="admin", email="admin@test.com", permissions=["demo.view"])
        pages = assembler.assemble([c], user=user)

        assert len(pages) == 1

    def test_public_page_visible_without_user(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = PageAssembler(naming_policy=naming, permission_filter=perms)

        c = _PublicPageContributor()
        pages = assembler.assemble([c])

        assert len(pages) == 1
        assert pages[0].name == "public.about"
