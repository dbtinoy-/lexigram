"""Tests for the Infrastructure center landing controller."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.controllers.infrastructure import InfrastructureController
from lexigram.admin.navigation.clusters import CLUSTER_GROUP
from lexigram.contracts.admin.types import NavigationContribution
from lexigram.ui import render_to_string


def _mock_request(groups: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.url.path = "/admin/infrastructure"
    state = MagicMock()
    state.assembler_groups = groups or {}
    request.app.state = state
    return request


def _groups() -> dict[str, list[NavigationContribution]]:
    return {
        CLUSTER_GROUP: [
            NavigationContribution(
                label="Web",
                url="/admin/web",
                icon="globe",
                group=CLUSTER_GROUP,
                children=(
                    NavigationContribution(
                        label="Routes",
                        url="/admin/web/routes",
                        icon="map",
                        group=CLUSTER_GROUP,
                    ),
                ),
            ),
            NavigationContribution(
                label="Cache",
                url="/admin/cache",
                icon="zap",
                group=CLUSTER_GROUP,
            ),
        ]
    }


def _render_page_returning_content(content: object, **_kwargs: object) -> MagicMock:
    return MagicMock(status_code=200, _content=content)


class TestInfrastructureController:
    @pytest.fixture
    def renderer(self) -> MagicMock:
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        return renderer

    @pytest.fixture
    def controller(self, renderer: MagicMock) -> InfrastructureController:
        return InfrastructureController(renderer=renderer)

    @pytest.mark.asyncio
    async def test_index_renders_cluster_cards(
        self, controller: InfrastructureController, renderer: MagicMock
    ) -> None:
        renderer.render_page.side_effect = _render_page_returning_content
        resp = await controller.index(_mock_request(groups=_groups()))
        assert resp.status_code == 200
        html = render_to_string(resp._content)
        assert "/admin/infrastructure/web" in html
        assert "/admin/infrastructure/cache" in html
        assert "/admin/infrastructure/web/routes" in html
        assert "HTTP routing, middleware, and web API endpoints." in html
        assert "Cache backends, keys, and TTL policies." in html

    @pytest.mark.asyncio
    async def test_index_renders_empty_state(
        self, controller: InfrastructureController, renderer: MagicMock
    ) -> None:
        renderer.render_page.side_effect = _render_page_returning_content
        resp = await controller.index(_mock_request(groups={}))
        assert resp.status_code == 200
        html = render_to_string(resp._content)
        assert "No Infrastructure Areas" in html

    @pytest.mark.asyncio
    async def test_index_wraps_content_with_secondary_nav_layout(
        self, renderer: MagicMock
    ) -> None:
        from unittest.mock import patch

        renderer.render_page.side_effect = _render_page_returning_content
        controller = InfrastructureController(renderer=renderer)
        secondary = [{"label": "Web", "href": "/admin/web", "active": False}]
        with patch(
            "lexigram.admin.engine.renderer.resolve_admin_nav",
            return_value=([], [], secondary),
        ):
            resp = await controller.index(_mock_request(groups=_groups()))
        assert resp.status_code == 200
        html = render_to_string(resp._content)
        assert 'class="flex flex-col md:flex-row gap-6"' in html
        assert "flex-1 min-w-0" in html
        assert "/admin/infrastructure/web" in html
        assert "/admin/infrastructure/cache" in html

    def test_render_overview_preserves_item_order(self) -> None:
        controller = InfrastructureController(renderer=MagicMock())
        html = render_to_string(controller._render_overview(_groups()[CLUSTER_GROUP]))
        assert html.index("/admin/infrastructure/web") < html.index(
            "/admin/infrastructure/cache"
        )

    def test_render_overview_shows_fallback_description(self) -> None:
        controller = InfrastructureController(renderer=MagicMock())
        groups = {
            CLUSTER_GROUP: [
                NavigationContribution(
                    label="Messaging",
                    url="/admin/messaging",
                    icon="mail",
                    group=CLUSTER_GROUP,
                ),
            ]
        }
        html = render_to_string(controller._render_overview(groups[CLUSTER_GROUP]))
        assert "Manage and monitor this infrastructure area." in html
