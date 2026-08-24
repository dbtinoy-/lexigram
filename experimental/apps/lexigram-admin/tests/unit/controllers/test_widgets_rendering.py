"""Tests for WidgetController rendering logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.widgets import WidgetController
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.contracts.admin.widget_content import MessageContent
from lexigram.result import Err, Ok


class TestWidgetController:
    @pytest.fixture
    def mock_registry(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_contributor(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_when_contributor_not_found(
        self, mock_registry: MagicMock
    ) -> None:
        mock_registry.get.return_value = None
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="nonexistent",
            widget_name="some_widget",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body
        assert b"Contributor" in response.body

    @pytest.mark.asyncio
    async def test_returns_html_on_ok_result(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(content=MessageContent(text="ok")))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="pool_utilization",
        )
        assert response.status_code == 200
        assert b"ok" in response.body

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_on_widget_not_found(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        from lexigram.contracts.admin.errors import WidgetNotFoundError

        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Err(WidgetNotFoundError("sql", "unknown_widget"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="unknown_widget",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_on_domain_error(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        from lexigram.contracts.admin.errors import AdminError

        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Err(AdminError("data unavailable"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="pool_utilization",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body
