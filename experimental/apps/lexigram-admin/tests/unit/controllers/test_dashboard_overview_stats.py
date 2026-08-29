"""Default overview stat-grid fragment endpoint.

``GET /widgets/stats`` backs ``StatsOverviewWidget(data_source=...)`` cards
with the same four headline stats as the inline default overview, rendered
through the shared content dispatcher.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.controllers.dashboard import DashboardController


def _request_with_resources(resources: dict) -> MagicMock:
    request = MagicMock()
    request.app.state.admin_resources = resources
    return request


class TestOverviewStats:
    @pytest.fixture
    def controller(self) -> DashboardController:
        return DashboardController(renderer=MagicMock(), assembler=None)

    @pytest.mark.asyncio
    async def test_renders_all_four_headline_stats(
        self,
        controller: DashboardController,
    ) -> None:
        response = await controller.overview_stats(
            _request_with_resources({"users": object(), "roles": object()})
        )
        html = response.body.decode("utf-8", "replace")
        assert "Resources" in html
        assert ">2<" in html
        assert "Active Now" in html
        assert "Actions Today" in html
        assert "Errors (24h)" in html

    @pytest.mark.asyncio
    async def test_zero_resources_renders_zero(self, controller: DashboardController) -> None:
        response = await controller.overview_stats(_request_with_resources({}))
        html = response.body.decode("utf-8", "replace")
        assert ">0<" in html
