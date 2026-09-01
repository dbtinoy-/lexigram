"""Tests for HTMX optimistic helpers (absorbed from features/optimistic.py)."""
from __future__ import annotations


def test_optimistic_update_helper() -> None:
    from lexigram.ui.htmx.helpers import optimistic_update
    result = optimistic_update("#target", "<span>loading…</span>")
    assert "hx-on::before-request" in result
    assert "#target" in result["hx-on::before-request"]


def test_hx_optimistic_swap_helper() -> None:
    from lexigram.ui.htmx.helpers import hx_optimistic_swap
    result = hx_optimistic_swap("#target", "<b>!</b>")
    assert "hx-on-click" in result
    assert "#target" in result["hx-on-click"]
    # Values are emitted as encoded JS literals, so an apostrophe needs no
    # backslash: it sits inside a double-quoted string.
    result_escaped = hx_optimistic_swap("#x", "it's")
    assert '"it\'s"' in result_escaped["hx-on-click"]
