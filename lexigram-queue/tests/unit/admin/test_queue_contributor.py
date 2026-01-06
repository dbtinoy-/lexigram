"""Test suite for QueueAdminContributor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.queue.admin.contributor import QueueAdminContributor
from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
from lexigram.queue.admin.handlers.failed_messages import FailedMessagesWidgetHandler
from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler
from lexigram.queue.admin.viewmodels import (
    ConsumerLagViewModel,
    FailedMessagesViewModel,
    QueueDepthViewModel,
)
from lexigram.result import Err, Ok


class TestQueueAdminContributor:
    """Test suite for QueueAdminContributor."""

    @pytest.fixture
    def mock_depth_handler(self) -> MagicMock:
        """Mock queue depth handler."""
        handler = MagicMock(spec=QueueDepthWidgetHandler)
        handler.get_data = AsyncMock(
            return_value=Ok(
                QueueDepthViewModel(depth=42, max_depth=100, queue_name="default")
            )
        )
        return handler

    @pytest.fixture
    def mock_lag_handler(self) -> MagicMock:
        """Mock consumer lag handler."""
        handler = MagicMock(spec=ConsumerLagWidgetHandler)
        handler.get_data = AsyncMock(
            return_value=Ok(ConsumerLagViewModel(lag_messages=10, lag_seconds=2.5))
        )
        return handler

    @pytest.fixture
    def mock_failed_handler(self) -> MagicMock:
        """Mock failed messages handler."""
        handler = MagicMock(spec=FailedMessagesWidgetHandler)
        handler.get_data = AsyncMock(
            return_value=Ok(FailedMessagesViewModel(count=0, oldest_age_minutes=None))
        )
        return handler

    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        """Mock Jinja2 renderer."""
        renderer = MagicMock()
        renderer.render = MagicMock(return_value="<div>rendered</div>")
        return renderer

    @pytest.fixture
    def mock_container(
        self,
        mock_depth_handler: MagicMock,
        mock_lag_handler: MagicMock,
        mock_failed_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> MagicMock:
        """Mock DI container that resolves handler classes."""
        from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
        from lexigram.queue.admin.handlers.failed_messages import (
            FailedMessagesWidgetHandler,
        )
        from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler
        from lexigram.queue.admin.renderer import PackageWidgetRenderer

        container = MagicMock()
        resolve_map = {
            QueueDepthWidgetHandler: mock_depth_handler,
            ConsumerLagWidgetHandler: mock_lag_handler,
            FailedMessagesWidgetHandler: mock_failed_handler,
            PackageWidgetRenderer: mock_renderer,
        }
        container.resolve = AsyncMock(side_effect=resolve_map.get)
        return container

    @pytest.fixture
    async def contributor(
        self,
        mock_container: MagicMock,
    ) -> QueueAdminContributor:
        """Create a contributor with zero-arg constructor and mock container boot."""
        contrib = QueueAdminContributor()
        await contrib.on_admin_boot(mock_container)
        return contrib

    def test_contributor_metadata(self, contributor: QueueAdminContributor) -> None:
        """Test contributor name and display properties."""
        assert contributor.name == "queue"
        assert contributor.display_name == "Queue"
        assert contributor.group == "infrastructure"
        assert contributor.priority == 35

    def test_get_dashboard_widgets(self, contributor: QueueAdminContributor) -> None:
        """Test that contributor provides exactly 3 widgets."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 3
        widget_names = {w.name for w in widgets}
        assert widget_names == {"queue_depth", "consumer_lag", "failed_messages"}

    def test_get_navigation_items(self, contributor: QueueAdminContributor) -> None:
        """Test that contributor provides navigation items."""
        items = contributor.get_navigation_items()
        assert len(items) > 0
        assert any(item.label == "Queue" for item in items)

    def test_get_health_definitions(self, contributor: QueueAdminContributor) -> None:
        """Test that contributor provides health checks."""
        defs = contributor.get_health_definitions()
        assert len(defs) > 0
        assert any("queue" in d.name for d in defs)

    def test_get_actions(self, contributor: QueueAdminContributor) -> None:
        """Test that contributor provides actions."""
        actions = contributor.get_actions()
        assert len(actions) > 0

    @pytest.mark.asyncio
    async def test_render_widget_queue_depth(
        self,
        contributor: QueueAdminContributor,
        mock_depth_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test rendering queue_depth widget."""
        params = WidgetParams()
        result = await contributor.render_widget("queue_depth", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>rendered</div>"
        mock_depth_handler.get_data.assert_awaited_once_with(params)
        mock_renderer.render.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_widget_consumer_lag(
        self,
        contributor: QueueAdminContributor,
        mock_lag_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test rendering consumer_lag widget."""
        params = WidgetParams()
        result = await contributor.render_widget("consumer_lag", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>rendered</div>"
        mock_lag_handler.get_data.assert_awaited_once_with(params)
        mock_renderer.render.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_widget_failed_messages(
        self,
        contributor: QueueAdminContributor,
        mock_failed_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test rendering failed_messages widget."""
        params = WidgetParams()
        result = await contributor.render_widget("failed_messages", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>rendered</div>"
        mock_failed_handler.get_data.assert_awaited_once_with(params)
        mock_renderer.render.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_widget_unknown_widget(
        self, contributor: QueueAdminContributor
    ) -> None:
        """Test rendering an unknown widget returns WidgetNotFoundError."""
        params = WidgetParams()
        result = await contributor.render_widget("unknown_widget", params)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)

    @pytest.mark.asyncio
    async def test_render_widget_handler_error(
        self, contributor: QueueAdminContributor, mock_depth_handler: MagicMock
    ) -> None:
        """Test that handler errors are propagated."""
        from lexigram.contracts.admin.errors import AdminError

        error = AdminError("Test error")
        mock_depth_handler.get_data = AsyncMock(return_value=Err(error))

        params = WidgetParams()
        result = await contributor.render_widget("queue_depth", params)

        assert result.is_err()
        assert result.unwrap_err() is error


__all__ = ["TestQueueAdminContributor"]
