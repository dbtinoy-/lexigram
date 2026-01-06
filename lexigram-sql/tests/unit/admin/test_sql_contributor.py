"""Unit tests for SqlAdminContributor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.contracts.admin.widget_protocols import WidgetHandlerProtocol
from lexigram.result import Ok
from lexigram.sql.admin.contributor import SqlAdminContributor
from lexigram.sql.admin.renderer import PackageWidgetRenderer
from lexigram.sql.admin.viewmodels import PoolUtilizationViewModel


class TestSqlAdminContributor:
    """Tests for SqlAdminContributor widget rendering."""

    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        """Create a mock Jinja2 renderer."""
        r = MagicMock(spec=PackageWidgetRenderer)
        r.render = MagicMock(return_value="<div>widget</div>")
        return r

    @pytest.fixture
    def mock_pool_handler(self) -> MagicMock:
        """Create a mock pool utilization handler."""
        h = MagicMock(spec=WidgetHandlerProtocol)
        h.get_data = AsyncMock(
            return_value=Ok(
                PoolUtilizationViewModel(
                    pool_size=20,
                    active_connections=8,
                    idle_connections=12,
                    utilization_pct=40.0,
                )
            )
        )
        return h

    @pytest.fixture
    def contributor(
        self, mock_pool_handler: MagicMock, mock_renderer: MagicMock
    ) -> SqlAdminContributor:
        """Create a contributor with mocked dependencies."""
        contrib = SqlAdminContributor()
        contrib._handlers = {
            "pool_utilization": mock_pool_handler,
            "query_stats": MagicMock(spec=WidgetHandlerProtocol),
            "migration_status": MagicMock(spec=WidgetHandlerProtocol),
        }
        contrib._renderer = mock_renderer
        return contrib

    @pytest.mark.asyncio
    async def test_render_widget_dispatches_to_handler(
        self,
        contributor: SqlAdminContributor,
        mock_pool_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test that render_widget dispatches to the correct handler."""
        result = await contributor.render_widget("pool_utilization", WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.body, str)
        assert vm.body == "<div>widget</div>"
        mock_pool_handler.get_data.assert_awaited_once()
        mock_renderer.render.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_widget_returns_not_found(
        self, contributor: SqlAdminContributor
    ) -> None:
        """Test that unknown widget names return WidgetNotFoundError."""
        result = await contributor.render_widget("nonexistent", WidgetParams())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)

    def test_get_dashboard_widgets_returns_three(
        self, contributor: SqlAdminContributor
    ) -> None:
        """Test that exactly three dashboard widgets are registered."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 3
        widget_names = {w.name for w in widgets}
        assert widget_names == {
            "pool_utilization",
            "query_stats",
            "migration_status",
        }

    def test_get_navigation_items_not_empty(
        self, contributor: SqlAdminContributor
    ) -> None:
        """Test that navigation items are returned."""
        items = contributor.get_navigation_items()
        assert len(items) > 0
        assert any(item.label == "Database" for item in items)

    def test_get_health_definitions_not_empty(
        self, contributor: SqlAdminContributor
    ) -> None:
        """Test that health definitions are returned."""
        defs = contributor.get_health_definitions()
        assert len(defs) > 0
        assert any("connectivity" in d.name for d in defs)

    def test_contributor_name_is_sql(self, contributor: SqlAdminContributor) -> None:
        """Test that contributor name is 'sql'."""
        assert contributor.name == "sql"

    def test_contributor_metadata(self, contributor: SqlAdminContributor) -> None:
        """Test contributor metadata fields."""
        assert contributor.display_name == "Database"
        assert contributor.group == "infrastructure"
        assert contributor.icon == "database"
        assert contributor.priority == 15
