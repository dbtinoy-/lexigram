from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.page_assembler import PageAssembler
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.types import AdminUser
from lexigram.contracts.admin import (
    BaseAdminContributor,
    ManagementPageDefinition,
    PageCategory,
)


class FakeContributor(BaseAdminContributor):
    name = "fake"
    display_name = "Fake"
    group = "test"
    icon = "i"
    priority = 100
    version = "0"
    package_source = "fake_pkg"
    required_permissions = frozenset()

    def get_management_pages(self):
        return [
            ManagementPageDefinition(
                name="users",
                title="Users",
                contributor="fake_pkg",
                route_path="/admin/fake/users",
                handler="",
                category=PageCategory.CONFIGURATION,
            ),
        ]


class RestrictedContributor(BaseAdminContributor):
    name = "restricted"
    display_name = "Restricted"
    group = "test"
    icon = "i"
    priority = 100
    version = "0"
    package_source = "restricted_pkg"
    required_permissions = frozenset()

    def get_management_pages(self):
        return [
            ManagementPageDefinition(
                name="admin_panel",
                title="Admin Panel",
                contributor="restricted_pkg",
                route_path="/admin/restricted/panel",
                handler="",
                category=PageCategory.CONFIGURATION,
                permission="admin.super",
            ),
        ]


def test_collects_pages_from_all_contributors() -> None:
    a = PageAssembler(
        naming_policy=NamingPolicy(),
        permission_filter=PermissionFilter(),
    )
    pages = a.assemble([FakeContributor()])
    assert len(pages) == 1
    assert pages[0].name == "fake_pkg.users"


def test_namespaces_page_names_by_package_source() -> None:
    a = PageAssembler(
        naming_policy=NamingPolicy(),
        permission_filter=PermissionFilter(),
    )
    pages = a.assemble([FakeContributor()])
    assert pages[0].name.startswith("fake_pkg.")


def test_permission_filter_hides_restricted_pages() -> None:
    a = PageAssembler(
        naming_policy=NamingPolicy(),
        permission_filter=PermissionFilter(),
    )
    user = AdminUser("1", "test", "test@ex.com", permissions=frozenset())
    pages = a.assemble(
        [FakeContributor(), RestrictedContributor()],
        user=user,
    )
    names = [p.name for p in pages]
    assert "fake_pkg.users" in names
    assert "restricted_pkg.admin_panel" not in names
