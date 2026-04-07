"""Integration tests: contributor settings panel assembly end-to-end."""

from __future__ import annotations

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.dashboard.route_integrator import RouteIntegrator
from lexigram.admin.dashboard.settings_assembler import SettingsPanelAssembler
from lexigram.admin.types import AdminUser
from lexigram.contracts.admin import (
    BaseAdminContributor,
    SettingsPanelDefinition,
)


class _RouteRecorder:
    def __init__(self) -> None:
        self.routes: list[dict] = []

    def add_route(self, path: str, method: str, handler: object, name: str) -> None:
        self.routes.append({"path": path, "method": method, "handler": handler, "name": name})


class _SettingsContributor(BaseAdminContributor):
    name = "mail"
    display_name = "Mail"
    group = "settings"
    icon = "mail"
    priority = 100
    version = "1.0.0"
    package_source = "mail"
    required_permissions = frozenset()

    def get_settings_panels(self):
        return [
            SettingsPanelDefinition(
                name="smtp",
                title="SMTP Settings",
                contributor="mail",
                route_path="/admin/mail/smtp",
                handler=lambda req: "smtp settings",
                permission="mail.configure",
            ),
        ]


class _PublicSettingsContributor(BaseAdminContributor):
    name = "general"
    display_name = "General"
    group = "settings"
    icon = "settings"
    priority = 100
    version = "1.0.0"
    package_source = "general"
    required_permissions = frozenset()

    def get_settings_panels(self):
        return [
            SettingsPanelDefinition(
                name="site",
                title="Site Settings",
                contributor="general",
                route_path="/admin/general/site",
                handler=lambda req: "site settings",
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


class TestContributorSettingsPanelEndToEnd:
    def test_settings_assembled_and_routes_registered(self) -> None:
        naming = NamingPolicy(mode="warn")
        recorder = _RouteRecorder()
        integrator = RouteIntegrator(router=recorder, naming_policy=naming)

        c = _SettingsContributor()
        integrator.register([c])

        settings_names = [r["name"] for r in recorder.routes if "mail" in r["name"]]
        assert any("mail.smtp" in name for name in settings_names)

    def test_settings_namespaced_by_package_source(self) -> None:
        naming = NamingPolicy(mode="error")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c = _PublicSettingsContributor()
        panels = assembler.assemble([c])

        assert len(panels) == 1
        assert panels[0].name == "general.site"

    def test_empty_contributor_yields_no_settings(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c = _EmptyContributor()
        panels = assembler.assemble([c])

        assert len(panels) == 0

    def test_settings_permission_filter_removes_restricted(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c = _SettingsContributor()
        user = AdminUser(id="1", username="test", email="test@test.com", permissions=[])
        panels = assembler.assemble([c], user=user)

        assert len(panels) == 0

    def test_settings_visible_to_user_with_permission(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c = _SettingsContributor()
        user = AdminUser(
            id="1", username="admin", email="admin@test.com", permissions=["mail.configure"]
        )
        panels = assembler.assemble([c], user=user)

        assert len(panels) == 1

    def test_public_setting_visible_without_user(self) -> None:
        naming = NamingPolicy(mode="warn")
        perms = PermissionFilter()
        assembler = SettingsPanelAssembler(naming_policy=naming, permission_filter=perms)

        c = _PublicSettingsContributor()
        panels = assembler.assemble([c])

        assert len(panels) == 1
        assert panels[0].name == "general.site"
