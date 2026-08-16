"""Tests for the lexigram-search admin contributor skeleton."""

from __future__ import annotations

from lexigram.search.admin import SearchAdminContributor


class TestSearchAdminContributor:
    """Tests for the admin contributor interface."""

    def test_contributor_identity(self) -> None:
        """The contributor exposes stable identity attributes."""
        c = SearchAdminContributor()
        assert c.name == "search"
        assert c.display_name == "Search"

    def test_empty_contributions(self) -> None:
        """Skeleton contributor reports no pages/widgets/actions yet."""
        c = SearchAdminContributor()
        assert c.get_management_pages() == []
        assert c.get_dashboard_widgets() == []
        assert c.get_actions() == []
        assert c.get_health_definitions() == []

    def test_navigation_points_at_global_search_page(self) -> None:
        """The contributor surfaces the admin search page in the nav."""
        c = SearchAdminContributor()
        items = c.get_navigation_items()
        assert len(items) == 1
        item = items[0]
        assert item.label == "Search"
        assert item.url == "/admin/search"
        assert item.icon == "search"

    def test_all_exports(self) -> None:
        """Verify SearchAdminContributor is exported from the admin package."""
        from lexigram.search.admin import __all__

        assert "SearchAdminContributor" in __all__
