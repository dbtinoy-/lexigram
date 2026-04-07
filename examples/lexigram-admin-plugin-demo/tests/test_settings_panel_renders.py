from __future__ import annotations

from demo.settings.demo_settings import DemoSettingsPanel


async def test_settings_panel_returns_page_response() -> None:
    panel = DemoSettingsPanel()
    response = await panel.view(request=None)
    assert response.title == "Demo Settings"
    assert response.content is not None


async def test_settings_panel_contains_expected_html() -> None:
    panel = DemoSettingsPanel()
    response = await panel.view(request=None)
    assert "<h2>Demo Settings</h2>" in response.content
    assert "contributed by the demo plugin" in response.content


async def test_settings_panel_has_correct_title_attribute() -> None:
    assert DemoSettingsPanel.title == "Demo Settings"


async def test_settings_panel_has_correct_path() -> None:
    assert DemoSettingsPanel.path == "/admin/demo/settings"
