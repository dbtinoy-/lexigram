"""Tests for EmptyState molecule."""
from __future__ import annotations

from lexigram.ui.core.base import el
from lexigram.ui.molecules.empty_state import EmptyState


class TestEmptyState:
    def test_render_default(self) -> None:
        e = EmptyState()
        result = str(e)
        assert "No data available" in result

    def test_render_custom_title(self) -> None:
        e = EmptyState(title="No results found")
        result = str(e)
        assert "No results found" in result

    def test_render_custom_message(self) -> None:
        e = EmptyState(message="Try a different filter.")
        result = str(e)
        assert "Try a different filter" in result

    def test_render_custom_icon(self) -> None:
        e = EmptyState(icon="🔍")
        result = str(e)
        assert "🔍" in result

    def test_render_named_icon_resolves_to_svg(self) -> None:
        e = EmptyState(icon="clock")
        result = str(e)
        assert "<svg" in result
        assert ">clock<" not in result

    def test_render_named_icon_preserves_wrapper(self) -> None:
        e = EmptyState(icon="alert-triangle")
        result = str(e)
        assert 'class="text-6xl mb-4 opacity-50"' in result
        assert "<svg" in result
        assert 'class="w-16 h-16' in result

    def test_render_with_action(self) -> None:
        action = el("a", "Create New", href="/new")
        e = EmptyState(action=action)
        result = str(e)
        assert "Create New" in result
        assert "/new" in result

    def test_render_no_action(self) -> None:
        e = EmptyState()
        result = str(e)
        assert "Create" not in result
