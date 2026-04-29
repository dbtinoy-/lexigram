"""Tests for the generic cluster center controller."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lexigram.admin.clusters import Cluster
from lexigram.admin.controllers.clusters import ClusterCenterController
from lexigram.contracts.admin.types import NavigationContribution
from lexigram.ui import render_to_string

CONTENT = Cluster(
    name="content",
    slug="content",
    group="content-group",
    label="Content",
    icon="document",
    description="All your content.",
)


def _mock_request(groups: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.url.path = "/admin/content"
    state = MagicMock()
    state.assembler_groups = groups or {}
    request.app.state = state
    return request


def _groups() -> dict[str, list[NavigationContribution]]:
    return {
        CONTENT.group: [
            NavigationContribution(
                label="Posts",
                url="/admin/posts",
                icon="box",
                group=CONTENT.group,
                children=(
                    NavigationContribution(
                        label="Post one",
                        url="/admin/posts/1",
                        icon="file",
                        group=CONTENT.group,
                    ),
                ),
            ),
            NavigationContribution(
                label="Pages",
                url="/admin/pages",
                icon="file",
                group=CONTENT.group,
            ),
        ]
    }


def _render_page_returning_content(content: object, **_kwargs: object) -> MagicMock:
    return MagicMock(status_code=200, _content=content)


class TestClusterCenterController:
    @pytest.fixture
    def controller(self) -> ClusterCenterController:
        return ClusterCenterController(renderer=MagicMock(), cluster=CONTENT)

    @pytest.mark.asyncio
    async def test_index_renders_landing_with_namespaced_links(
        self, controller: ClusterCenterController
    ) -> None:
        controller.renderer.render_page.side_effect = _render_page_returning_content
        resp = await controller.index(_mock_request(groups=_groups()))
        assert resp.status_code == 200
        html = render_to_string(resp._content)
        assert "/admin/content/posts" in html
        assert "/admin/content/pages" in html
        assert "/admin/content/posts/1" in html
        assert "Content" in html
        assert "All your content." in html

    @pytest.mark.asyncio
    async def test_index_uses_cluster_label_in_empty_state(
        self, controller: ClusterCenterController
    ) -> None:
        controller.renderer.render_page.side_effect = _render_page_returning_content
        resp = await controller.index(_mock_request(groups={}))
        assert resp.status_code == 200
        html = render_to_string(resp._content)
        assert "No Content Areas" in html

    @pytest.mark.asyncio
    async def test_index_wraps_content_with_secondary_nav_layout(
        self, controller: ClusterCenterController
    ) -> None:
        controller.renderer.render_page.side_effect = _render_page_returning_content
        secondary = [{"label": "Posts", "href": "/admin/content/posts", "active": True}]
        with patch(
            "lexigram.admin.engine.renderer.resolve_admin_nav",
            return_value=([], [], secondary),
        ):
            resp = await controller.index(_mock_request(groups=_groups()))
        assert resp.status_code == 200
        html = render_to_string(resp._content)
        assert "/admin/content/posts" in html

    def test_prefix_uses_cluster_slug(self) -> None:
        controller = ClusterCenterController(renderer=MagicMock(), cluster=CONTENT)
        assert controller.prefix == "/content"