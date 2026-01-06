"""Tests for cache admin contributor."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.cache.admin.contributor import CacheAdminContributor
from lexigram.cache.admin.viewmodels import (
    BackendPingViewModel,
    EvictionRateViewModel,
    HitMissRatioViewModel,
)
from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Err, Ok


class TestCacheAdminContributor:
    """Test suite for CacheAdminContributor."""

    @pytest.fixture
    def mock_hit_miss_handler(self) -> MagicMock:
        """Mock hit/miss handler."""
        handler = MagicMock()
        handler.get_data = AsyncMock(
            return_value=Ok(
                HitMissRatioViewModel(
                    hits=100, misses=20, hit_rate_pct=83.3, window_minutes=60
                )
            )
        )
        return handler

    @pytest.fixture
    def mock_eviction_handler(self) -> MagicMock:
        """Mock eviction rate handler."""
        handler = MagicMock()
        handler.get_data = AsyncMock(
            return_value=Ok(
                EvictionRateViewModel(evictions_per_second=0.5, total_evictions=30)
            )
        )
        return handler

    @pytest.fixture
    def mock_ping_handler(self) -> MagicMock:
        """Mock backend ping handler."""
        handler = MagicMock()
        handler.get_data = AsyncMock(
            return_value=Ok(
                BackendPingViewModel(
                    latency_ms=1.23, is_reachable=True, backend_name="memory"
                )
            )
        )
        return handler

    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        """Mock Jinja2 widget renderer."""
        renderer = MagicMock()
        renderer.render = MagicMock(return_value="<div>Rendered HTML</div>")
        return renderer

    @pytest.fixture
    def contributor(
        self,
        mock_hit_miss_handler: MagicMock,
        mock_eviction_handler: MagicMock,
        mock_ping_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> CacheAdminContributor:
        """Create contributor with mocked handlers and renderer."""
        contrib = CacheAdminContributor()
        contrib._handlers = {
            "hit_miss_ratio": mock_hit_miss_handler,
            "eviction_rate": mock_eviction_handler,
            "backend_ping": mock_ping_handler,
        }
        contrib._renderer = mock_renderer
        return contrib

    def test_contributor_metadata(self, contributor: CacheAdminContributor) -> None:
        """Test contributor metadata properties."""
        assert contributor.name == "cache"
        assert contributor.display_name == "Cache"
        assert contributor.group == "infrastructure"
        assert contributor.icon == "zap"
        assert contributor.priority == 20

    def test_dashboard_widgets_count(self, contributor: CacheAdminContributor) -> None:
        """Test that contributor returns all three widgets."""
        widgets = contributor.get_dashboard_widgets()
        widget_names = [w.name for w in widgets]
        assert "hit_miss_ratio" in widget_names
        assert "eviction_rate" in widget_names
        assert "backend_ping" in widget_names
        assert len(widgets) == 3

    @pytest.mark.asyncio
    async def test_render_hit_miss_ratio_widget(
        self,
        contributor: CacheAdminContributor,
        mock_hit_miss_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> None:
        """Test rendering the hit/miss ratio widget."""
        params = WidgetParams(time_window_minutes=60)
        result = await contributor.render_widget("hit_miss_ratio", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>Rendered HTML</div>"

        # Verify handler was called
        mock_hit_miss_handler.get_data.assert_awaited_once_with(params)

        # Verify renderer was called with viewmodel dict
        mock_renderer.render.assert_called_once()
        call_args = mock_renderer.render.call_args
        assert call_args[0][0] == "hit_miss_ratio.html"
        # context should be a dict with viewmodel attributes
        context = call_args[0][1]
        assert context["hits"] == 100
        assert context["misses"] == 20

    @pytest.mark.asyncio
    async def test_render_eviction_rate_widget(
        self,
        contributor: CacheAdminContributor,
        mock_eviction_handler: MagicMock,
    ) -> None:
        """Test rendering the eviction rate widget."""
        params = WidgetParams()
        result = await contributor.render_widget("eviction_rate", params)

        assert result.is_ok()
        mock_eviction_handler.get_data.assert_awaited_once_with(params)

    @pytest.mark.asyncio
    async def test_render_backend_ping_widget(
        self,
        contributor: CacheAdminContributor,
        mock_ping_handler: MagicMock,
    ) -> None:
        """Test rendering the backend ping widget."""
        params = WidgetParams()
        result = await contributor.render_widget("backend_ping", params)

        assert result.is_ok()
        mock_ping_handler.get_data.assert_awaited_once_with(params)

    @pytest.mark.asyncio
    async def test_render_unknown_widget_returns_not_found(
        self, contributor: CacheAdminContributor
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
        contributor: CacheAdminContributor,
        mock_hit_miss_handler: MagicMock,
    ) -> None:
        """Test that handler errors propagate through render_widget."""
        from lexigram.contracts.infra.cache.exceptions import CacheError

        error = CacheError("Backend unavailable")
        mock_hit_miss_handler.get_data = AsyncMock(return_value=Err(error))

        params = WidgetParams()
        result = await contributor.render_widget("hit_miss_ratio", params)

        assert result.is_err()
        returned_error = result.unwrap_err()
        assert returned_error is error

    @pytest.mark.asyncio
    async def test_render_widget_no_renderer_returns_not_found(
        self,
        mock_hit_miss_handler: MagicMock,
        mock_eviction_handler: MagicMock,
        mock_ping_handler: MagicMock,
    ) -> None:
        """Test that missing renderer returns not found."""
        contributor = CacheAdminContributor()
        contributor._handlers = {
            "hit_miss_ratio": mock_hit_miss_handler,
            "eviction_rate": mock_eviction_handler,
            "backend_ping": mock_ping_handler,
        }
        contributor._renderer = None

        params = WidgetParams()
        result = await contributor.render_widget("hit_miss_ratio", params)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)


__all__ = ["TestCacheAdminContributor"]
