"""Tests for CoreAdminContributor's System Info settings panel."""

from __future__ import annotations

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.contracts.admin import PageContent, SettingsPanelDefinition
from lexigram.contracts.admin.widget_content import TableContent
from lexigram.contracts.core import HealthStatus


class _FakeHealthRegistry:
    async def run_all(self) -> tuple[object, dict[str, object]]:
        return (HealthStatus.HEALTHY, {})


async def test_get_settings_panels_returns_system_info_panel() -> None:
    contributor = CoreAdminContributor()
    panels = contributor.get_settings_panels()
    assert len(panels) == 1
    panel = panels[0]
    assert isinstance(panel, SettingsPanelDefinition)
    assert panel.name == "system-info"
    assert panel.contributor == contributor.package_source


async def test_system_info_panel_handler_returns_page_content() -> None:
    contributor = CoreAdminContributor(health=_FakeHealthRegistry())
    panel = contributor.get_settings_panels()[0]
    page = await panel.handler.handle(request=None)
    assert isinstance(page, PageContent)
    assert isinstance(page.body, TableContent)
    fields = {row[0].text for row in page.body.rows}
    assert "Health Status" in fields
    values = {row[0].text: row[1].text for row in page.body.rows}
    assert values["Health Status"] == "healthy"


async def test_system_info_panel_handler_degrades_without_health_registry() -> None:
    contributor = CoreAdminContributor()
    panel = contributor.get_settings_panels()[0]
    page = await panel.handler.handle(request=None)
    values = {row[0].text: row[1].text for row in page.body.rows}
    assert values["Health Status"] == "unknown"
