"""Tests for UI optimistic module (absorbed from features/optimistic.py)."""

import json

from lexigram.ui.htmx.helpers import hx_optimistic_swap, optimistic_update


def _swapped_html(expression: str) -> str:
    """Decode the JS literal assigned to innerHTML.

    Angle brackets are emitted as \\u003c so the value can never close a
    surrounding script element, so the markup is compared after decoding
    rather than by substring.
    """
    literal = expression.split(".innerHTML = ", 1)[1]
    return json.loads(literal)


class TestOptimisticUpdate:
    def test_optimistic_update_basic(self) -> None:
        result = optimistic_update("#target", "<span>New content</span>")
        assert "hx-on::before-request" in result
        assert "#target" in result["hx-on::before-request"]
        assert _swapped_html(result["hx-on::before-request"]) == (
            "<span>New content</span>"
        )

    def test_optimistic_update_with_kwargs(self) -> None:
        result = optimistic_update("#target", "content", id="my-element", class_="active")
        assert result.get("id") == "my-element"
        assert result.get("class_") == "active"


class TestHxOptimisticSwap:
    def test_hx_optimistic_swap_basic(self) -> None:
        result = hx_optimistic_swap("#target", "<div>Hello</div>")
        assert "hx-on-click" in result
        assert "#target" in result["hx-on-click"]
        assert _swapped_html(result["hx-on-click"]) == "<div>Hello</div>"

    def test_hx_optimistic_swap_encodes_quotes(self) -> None:
        result = hx_optimistic_swap("#target", "it's working")

        assert '"it\'s working"' in result["hx-on-click"]

    def test_hx_optimistic_swap_rejects_breakout(self) -> None:
        """A backslash used to defeat the old hand-rolled escaping."""
        result = hx_optimistic_swap("#target", "\\';alert(1);//")

        assert "');alert(1);//" not in result["hx-on-click"]

    def test_hx_optimistic_swap_returns_dict(self) -> None:
        result = hx_optimistic_swap(".btn", "clicked!")
        assert isinstance(result, dict)
