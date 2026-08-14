"""Tests for Breadcrumbs molecule."""
from __future__ import annotations

from lexigram.ui.molecules.breadcrumbs import Breadcrumbs


class TestBreadcrumbs:
    def test_renders_home_icon(self) -> None:
        b = Breadcrumbs(items=[])
        result = str(b)
        assert "Breadcrumb" in result

    def test_renders_single_item(self) -> None:
        b = Breadcrumbs(items=[{"label": "Dashboard", "url": "/admin"}])
        result = str(b)
        assert "Dashboard" in result
        assert "/admin" in result

    def test_renders_multiple_items(self) -> None:
        b = Breadcrumbs(
            items=[
                {"label": "Dashboard", "url": "/admin"},
                {"label": "Users", "url": "/admin/users"},
                {"label": "Edit"},
            ]
        )
        result = str(b)
        assert "Dashboard" in result
        assert "Users" in result
        assert "Edit" in result

    def test_last_item_no_hx_attrs(self) -> None:
        b = Breadcrumbs(
            items=[
                {"label": "Dashboard", "url": "/admin"},
                {"label": "Current Page", "url": "/admin/current"},
            ]
        )
        result = str(b)
        assert "hx-get" not in result or "Current Page" in result
