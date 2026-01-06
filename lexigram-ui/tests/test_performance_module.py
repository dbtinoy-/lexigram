"""Tests for performance module."""

from __future__ import annotations


def test_performance_module_exports_render_cache() -> None:
    from lexigram.ui.performance.performance import RenderCache

    assert RenderCache is not None
