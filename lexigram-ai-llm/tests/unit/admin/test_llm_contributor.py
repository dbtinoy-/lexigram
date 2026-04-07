"""Unit tests for LlmAdminContributor widget rendering."""

from __future__ import annotations

import pytest

from lexigram.ai.llm.admin.contributor import LlmAdminContributor
from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel


class TestLlmAdminContributor:
    """Tests for LlmAdminContributor widget rendering."""

    @pytest.fixture
    def contributor(self) -> LlmAdminContributor:
        """Create a fresh contributor instance."""
        return LlmAdminContributor()

    @pytest.mark.asyncio
    async def test_render_widget_token_usage(
        self, contributor: LlmAdminContributor
    ) -> None:
        """Test rendering token_usage widget returns Ok with WidgetViewModel."""
        result = await contributor.render_widget("token_usage", WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)

    @pytest.mark.asyncio
    async def test_unknown_widget_returns_not_found(
        self, contributor: LlmAdminContributor
    ) -> None:
        """Test that unknown widget names return WidgetNotFoundError."""
        result = await contributor.render_widget("nonexistent", WidgetParams())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)

    def test_get_dashboard_widgets_returns_three(
        self, contributor: LlmAdminContributor
    ) -> None:
        """Test that exactly three dashboard widgets are registered."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 3
        widget_names = {w.name for w in widgets}
        assert widget_names == {"token_usage", "provider_status", "error_rate"}
