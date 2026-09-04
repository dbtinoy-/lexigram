from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.dashboard.settings_assembler import SettingsPanelAssembler
from lexigram.contracts.admin import (
    BaseAdminContributor,
    SettingsPanelDefinition,
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

    def get_settings_panels(self):
        return [
            SettingsPanelDefinition(
                name="general",
                title="General Settings",
                contributor="fake_pkg",
                route_path="/admin/fake/settings/general",
                handler="fake_pkg.module:func",
                order=37,
            ),
        ]


def test_collects_settings_from_all_contributors() -> None:
    a = SettingsPanelAssembler(
        naming_policy=NamingPolicy(),
        permission_filter=PermissionFilter(),
    )
    panels = a.assemble([FakeContributor()])
    assert len(panels) == 1
    assert panels[0].name == "fake_pkg.general"
