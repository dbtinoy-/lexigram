"""Contributor settings-panel links in the Configuration Center sidebar.

R50 (docs/09-01-2026/46-settings-panel-links.md): the sidebar renders the
union of ConfigRegistry spec categories and contributor-owned settings
panels (e.g. the core contributor's System Info page). Panels are mapped
to plain ``PanelLink`` values at the presentation layer; failures degrade
to a spec-only sidebar.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.settings.panel.layout import ConfigLayout
from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.panel.types import PanelLink
from lexigram.ui import render_to_string


def _mock_request(user: object | None = None) -> MagicMock:
    req = MagicMock(spec=Request)
    req.__len__ = lambda _self: 1
    req.method = "GET"
    req.headers = {}
    req.query_params = {}
    req.path_params = {}
    req.scope = {}
    req.state = MagicMock(user=user)
    return req


def _panel(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "name": "system-info",
        "title": "System Info",
        "contributor": "lexigram-admin",
        "route_path": "/admin/system/info",
        "icon": "info",
        "category": "System",
        "order": 10,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestPanelLinkType:
    def test_defaults(self) -> None:
        link = PanelLink(title="System Info", url="/admin/system/info")
        assert link.icon == "file-text"
        assert link.category == "Tools"

    def test_is_immutable(self) -> None:
        link = PanelLink(title="System Info", url="/admin/system/info")
        with pytest.raises(AttributeError):
            link.title = "Other"  # type: ignore[misc]


class TestConfigLayoutPanelLinks:
    def test_no_panel_links_renders_identically_to_before(self) -> None:
        without = render_to_string(ConfigLayout(categories=[]))
        empty = render_to_string(ConfigLayout(categories=[], panel_links=[]))
        none = render_to_string(ConfigLayout(categories=[], panel_links=None))
        assert without == empty == none
        assert "settings-panel-links" not in without

    def test_panel_link_rendered_with_htmx_navigation(self) -> None:
        html = render_to_string(
            ConfigLayout(
                categories=[],
                panel_links=[
                    PanelLink(
                        title="System Info",
                        url="/admin/system/info",
                        icon="info",
                        category="System",
                    )
                ],
            )
        )
        assert 'data-testid="settings-panel-links"' in html
        assert "System Info" in html
        assert 'href="/admin/system/info"' in html
        assert 'hx-get="/admin/system/info"' in html
        assert 'hx-target="#main-content"' in html
        assert 'hx-swap="innerHTML"' in html
        assert 'hx-push-url="true"' in html
        assert "data-admin-navigation" in html
        assert "data-settings-nav" in html

    def test_panel_links_grouped_by_category_in_sorted_order(self) -> None:
        html = render_to_string(
            ConfigLayout(
                categories=[],
                panel_links=[
                    PanelLink(title="Zeta", url="/admin/z", category="Zone"),
                    PanelLink(title="Alpha", url="/admin/a", category="Apps"),
                    PanelLink(title="Beta", url="/admin/b", category="Apps"),
                ],
            )
        )
        assert html.index("Apps") < html.index("Zone")
        assert html.index("Alpha") < html.index("Beta") < html.index("Zeta")
        assert html.count('data-testid="settings-panel-links"') == 2

    def test_panel_groups_render_after_spec_categories(self) -> None:
        from lexigram.admin.settings.panel.types import ConfigCategory

        category = ConfigCategory(
            name="lexigram-admin", label="Lexigram Admin", specs=[]
        )
        html = render_to_string(
            ConfigLayout(
                categories=[category],
                panel_links=[
                    PanelLink(title="System Info", url="/admin/system/info")
                ],
            )
        )
        assert html.index("Lexigram Admin") < html.index("System Info")


class TestControllerPanelLinks:
    def _controller(self, dashboard: object = None) -> SettingsController:
        return SettingsController(
            renderer=MagicMock(),
            registry=ConfigRegistry.with_defaults(),
            dashboard=dashboard,
        )

    @pytest.mark.asyncio
    async def test_no_dashboard_returns_empty(self) -> None:
        controller = self._controller(dashboard=None)
        assert await controller._panel_links(_mock_request()) == []

    @pytest.mark.asyncio
    async def test_panels_mapped_to_links(self) -> None:
        dashboard = SimpleNamespace(
            get_settings_panels=AsyncMock(return_value=[_panel()])
        )
        controller = self._controller(dashboard=dashboard)
        links = await controller._panel_links(_mock_request())
        assert links == [
            PanelLink(
                title="System Info",
                url="/admin/system/info",
                icon="info",
                category="System",
            )
        ]

    @pytest.mark.asyncio
    async def test_panel_urls_follow_custom_admin_prefix(self) -> None:
        dashboard = SimpleNamespace(
            get_settings_panels=AsyncMock(return_value=[_panel()])
        )
        controller = self._controller(dashboard=dashboard)
        request = _mock_request()
        request.scope = {"admin_prefix": "/backoffice"}

        links = await controller._panel_links(request)

        assert [link.url for link in links] == ["/backoffice/system/info"]

    @pytest.mark.asyncio
    async def test_current_user_forwarded_for_permission_filtering(self) -> None:
        user = SimpleNamespace(permissions=frozenset(), roles=[])
        dashboard = SimpleNamespace(get_settings_panels=AsyncMock(return_value=[]))
        controller = self._controller(dashboard=dashboard)
        await controller._panel_links(_mock_request(user=user))
        dashboard.get_settings_panels.assert_awaited_once_with(user)

    @pytest.mark.asyncio
    async def test_panels_sorted_by_order_then_title(self) -> None:
        dashboard = SimpleNamespace(
            get_settings_panels=AsyncMock(
                return_value=[
                    _panel(name="b", title="Bravo", order=50),
                    _panel(name="a", title="Alpha", order=50),
                    _panel(name="c", title="Charlie", order=10),
                ]
            )
        )
        controller = self._controller(dashboard=dashboard)
        links = await controller._panel_links(_mock_request())
        assert [link.title for link in links] == ["Charlie", "Alpha", "Bravo"]

    @pytest.mark.asyncio
    async def test_blank_icon_and_category_fall_back(self) -> None:
        dashboard = SimpleNamespace(
            get_settings_panels=AsyncMock(
                return_value=[_panel(icon="", category="")]
            )
        )
        controller = self._controller(dashboard=dashboard)
        links = await controller._panel_links(_mock_request())
        assert links[0].icon == "file-text"
        assert links[0].category == "Tools"

    @pytest.mark.asyncio
    async def test_panel_without_route_is_skipped(self) -> None:
        dashboard = SimpleNamespace(
            get_settings_panels=AsyncMock(return_value=[_panel(route_path="")])
        )
        controller = self._controller(dashboard=dashboard)
        assert await controller._panel_links(_mock_request()) == []

    @pytest.mark.asyncio
    async def test_dashboard_failure_degrades_to_empty(self) -> None:
        dashboard = SimpleNamespace(
            get_settings_panels=AsyncMock(side_effect=RuntimeError("boom"))
        )
        controller = self._controller(dashboard=dashboard)
        assert await controller._panel_links(_mock_request()) == []
