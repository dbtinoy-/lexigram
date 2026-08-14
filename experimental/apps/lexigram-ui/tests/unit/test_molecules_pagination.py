"""Tests for Pagination molecule."""
from __future__ import annotations

from lexigram.ui.molecules.pagination import Pagination


class TestPagination:
    def test_single_page_returns_empty(self) -> None:
        p = Pagination(page=1, total=5, per_page=20)
        assert str(p) == ""

    def test_two_pages_shows_navigation(self) -> None:
        p = Pagination(page=1, total=25, per_page=20)
        result = str(p)
        assert "Previous" in result
        assert "Next" in result

    def test_current_page_mid(self) -> None:
        p = Pagination(page=2, total=50, per_page=10)
        result = str(p)
        assert "Page 2 of 5" in result

    def test_last_page_disables_next(self) -> None:
        p = Pagination(page=5, total=50, per_page=10)
        result = str(p)
        assert "cursor-not-allowed" in result  # Next is disabled
        assert "Previous" in result

    def test_first_page_disables_previous(self) -> None:
        p = Pagination(page=1, total=50, per_page=10)
        result = str(p)
        assert "cursor-not-allowed" in result  # Previous is disabled
        assert "Next" in result

    def test_page_url_with_query_string(self) -> None:
        p = Pagination(page=1, total=50, per_page=10, base_url="/items?sort=asc")
        result = str(p)
        assert "page=" in result

    def test_hide_summary(self) -> None:
        p = Pagination(
            page=1, total=50, per_page=10, show_summary=False
        )
        result = str(p)
        assert "Showing" not in result

    def test_show_summary(self) -> None:
        p = Pagination(page=1, total=50, per_page=10, show_summary=True)
        result = str(p)
        assert "Showing" in result

    def test_total_pages_property(self) -> None:
        p = Pagination(page=1, total=100, per_page=30)
        assert p.total_pages == 4

    def test_total_pages_exact_division(self) -> None:
        p = Pagination(page=1, total=100, per_page=20)
        assert p.total_pages == 5

    def test_zero_total(self) -> None:
        p = Pagination(page=1, total=0, per_page=20)
        assert str(p) == ""

    def test_negative_page_clamps_to_one(self) -> None:
        p = Pagination(page=-1, total=50, per_page=10)
        assert p.page == 1
