"""Registered-resources chart endpoint on the dashboard controller.

The default overview wires a ``ChartWidget`` to ``/widgets/resources``; the
endpoint must return a bar-chart fragment (or an empty state when nothing is
registered) without raising.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request as StarletteRequest

from lexigram.admin.controllers.dashboard import DashboardController


def _request() -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/admin/widgets/resources",
        "raw_path": b"/admin/widgets/resources",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": MagicMock(),
        "session": {},
    }
    return StarletteRequest(scope)


def _request_with_resources(resources: dict) -> MagicMock:
    request = MagicMock()
    request.app.state.admin_resources = resources
    return request


class TestResourcesChart:
    @pytest.fixture
    def controller(self) -> DashboardController:
        return DashboardController(renderer=MagicMock(), assembler=None)

    @pytest.mark.asyncio
    async def test_renders_bar_chart_with_resource_names(
        self,
        controller: DashboardController,
    ) -> None:
        request = _request_with_resources(
            {
                "users": object(),
                "roles": object(),
            }
        )
        response = await controller.resources_chart(request)
        html = response.body.decode("utf-8", "replace")
        assert "users" in html
        assert "roles" in html
        assert "role=\"img\"" in html

    @pytest.mark.asyncio
    async def test_renders_empty_state_when_no_resources(
        self,
        controller: DashboardController,
    ) -> None:
        request = _request_with_resources({})
        response = await controller.resources_chart(request)
        html = response.body.decode("utf-8", "replace")
        assert "No resources" in html
        assert "No admin resources are registered yet." in html
