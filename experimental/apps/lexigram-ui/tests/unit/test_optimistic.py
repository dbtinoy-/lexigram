"""Tests for UI optimistic module (absorbed from features/optimistic.py)."""

from lexigram.ui.htmx.helpers import hx_optimistic_swap, optimistic_update


class TestOptimisticUpdate:
    def test_optimistic_update_basic(self) -> None:
        result = optimistic_update("#target", "<span>New content</span>")
        assert "hx-on::before-request" in result
        assert "#target" in result["hx-on::before-request"]
        assert "<span>New content</span>" in result["hx-on::before-request"]

    def test_optimistic_update_with_kwargs(self) -> None:
        result = optimistic_update("#target", "content", id="my-element", class_="active")
        assert result.get("id") == "my-element"
        assert result.get("class_") == "active"


class TestHxOptimisticSwap:
    def test_hx_optimistic_swap_basic(self) -> None:
        result = hx_optimistic_swap("#target", "<div>Hello</div>")
        assert "hx-on-click" in result
        assert "#target" in result["hx-on-click"]
        assert "<div>Hello</div>" in result["hx-on-click"]

    def test_hx_optimistic_swap_escapes_quotes(self) -> None:
        result = hx_optimistic_swap("#target", "it's working")
        assert "it\\'s working" in result["hx-on-click"]

    def test_hx_optimistic_swap_returns_dict(self) -> None:
        result = hx_optimistic_swap(".btn", "clicked!")
        assert isinstance(result, dict)
