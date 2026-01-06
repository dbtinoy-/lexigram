"""Tests for TasksAdminContributor widget rendering."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.result import Err, Ok
from lexigram.tasks.admin.contributor import TasksAdminContributor
from lexigram.tasks.admin.viewmodels import (
    AvgDurationViewModel,
    TasksSummaryViewModel,
)


@pytest.fixture
def mock_tasks_summary_handler() -> MagicMock:
    """Create mock tasks summary handler."""
    handler = MagicMock()
    handler.get_data = AsyncMock(
        return_value=Ok(
            TasksSummaryViewModel(
                pending=10,
                running=5,
                completed=100,
                failed=2,
            )
        )
    )
    return handler


@pytest.fixture
def mock_avg_duration_handler() -> MagicMock:
    """Create mock average duration handler."""
    handler = MagicMock()
    handler.get_data = AsyncMock(
        return_value=Ok(
            AvgDurationViewModel(
                avg_ms=250.5,
                p95_ms=500.2,
                window_minutes=60,
            )
        )
    )
    return handler


@pytest.fixture
def mock_renderer() -> MagicMock:
    """Create mock renderer."""
    renderer = MagicMock()
    renderer.render = MagicMock(return_value="<div>Rendered HTML</div>")
    return renderer


@pytest.fixture
def contributor(
    mock_tasks_summary_handler: MagicMock,
    mock_avg_duration_handler: MagicMock,
    mock_renderer: MagicMock,
) -> TasksAdminContributor:
    """Create TasksAdminContributor with mocked dependencies."""
    contrib = TasksAdminContributor()
    contrib._handlers = {
        "tasks_summary": mock_tasks_summary_handler,
        "avg_duration": mock_avg_duration_handler,
    }
    contrib._renderer = mock_renderer
    return contrib


class TestTasksAdminContributor:
    """Test suite for TasksAdminContributor."""

    @pytest.mark.asyncio
    async def test_render_tasks_summary_widget(
        self,
        contributor: TasksAdminContributor,
        mock_tasks_summary_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test rendering the tasks summary widget."""
        params = WidgetParams(time_window_minutes=60)
        result = await contributor.render_widget("tasks_summary", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>Rendered HTML</div>"

        # Verify handler was called
        mock_tasks_summary_handler.get_data.assert_awaited_once_with(params)

        # Verify renderer was called with viewmodel dict
        mock_renderer.render.assert_called_once()
        call_args = mock_renderer.render.call_args
        assert call_args[0][0] == "tasks_summary.html"
        # context should be a dict with viewmodel attributes
        context = call_args[0][1]
        assert context["pending"] == 10
        assert context["running"] == 5
        assert context["completed"] == 100
        assert context["failed"] == 2

    @pytest.mark.asyncio
    async def test_render_avg_duration_widget(
        self,
        contributor: TasksAdminContributor,
        mock_avg_duration_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test rendering the average duration widget."""
        params = WidgetParams(time_window_minutes=60)
        result = await contributor.render_widget("avg_duration", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>Rendered HTML</div>"

        # Verify handler was called
        mock_avg_duration_handler.get_data.assert_awaited_once_with(params)

        # Verify renderer was called with viewmodel dict
        mock_renderer.render.assert_called_once()
        call_args = mock_renderer.render.call_args
        assert call_args[0][0] == "avg_duration.html"
        # context should be a dict with viewmodel attributes
        context = call_args[0][1]
        assert context["avg_ms"] == 250.5
        assert context["p95_ms"] == 500.2
        assert context["window_minutes"] == 60

    @pytest.mark.asyncio
    async def test_render_unknown_widget_returns_not_found(
        self, contributor: TasksAdminContributor
    ) -> None:
        """Test that rendering an unknown widget returns WidgetNotFoundError."""
        params = WidgetParams()
        result = await contributor.render_widget("unknown_widget", params)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)

    @pytest.mark.asyncio
    async def test_render_widget_handler_error_propagates(
        self,
        contributor: TasksAdminContributor,
        mock_tasks_summary_handler: MagicMock,
    ) -> None:
        """Test that handler errors propagate through render_widget."""
        from lexigram.contracts.admin.errors import AdminError

        error = AdminError("Handler failed")
        mock_tasks_summary_handler.get_data = AsyncMock(return_value=Err(error))

        params = WidgetParams()
        result = await contributor.render_widget("tasks_summary", params)

        assert result.is_err()
        returned_error = result.unwrap_err()
        assert returned_error is error

    @pytest.mark.asyncio
    async def test_render_widget_handler_error_format(
        self,
        mock_tasks_summary_handler: MagicMock,
        mock_avg_duration_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test that handler data is rendered with correct template name."""
        from lexigram.tasks.admin.viewmodels import TasksSummaryViewModel

        handler = MagicMock()
        handler.get_data = AsyncMock(
            return_value=Ok(
                TasksSummaryViewModel(
                    pending=5,
                    running=2,
                    completed=50,
                    failed=1,
                )
            )
        )
        contributor = TasksAdminContributor()
        contributor._handlers = {
            "tasks_summary": handler,
            "avg_duration": mock_avg_duration_handler,
        }
        contributor._renderer = mock_renderer

        params = WidgetParams()
        result = await contributor.render_widget("tasks_summary", params)

        assert result.is_ok()
        mock_renderer.render.assert_called_once()
        call_args = mock_renderer.render.call_args
        assert call_args[0][0] == "tasks_summary.html"

    def test_get_dashboard_widgets_returns_two_widgets(
        self, contributor: TasksAdminContributor
    ) -> None:
        """Test that contributor returns exactly 2 dashboard widgets."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 2

        widget_names = {w.name for w in widgets}
        assert widget_names == {"tasks_summary", "avg_duration"}

    def test_get_navigation_items(self, contributor: TasksAdminContributor) -> None:
        """Test that contributor returns navigation items."""
        nav_items = contributor.get_navigation_items()
        assert len(nav_items) > 0

    def test_get_health_definitions(self, contributor: TasksAdminContributor) -> None:
        """Test that contributor returns health definitions."""
        health_defs = contributor.get_health_definitions()
        assert len(health_defs) > 0

    def test_get_actions(self, contributor: TasksAdminContributor) -> None:
        """Test that contributor returns actions."""
        actions = contributor.get_actions()
        assert len(actions) > 0


__all__ = ["TestTasksAdminContributor"]
