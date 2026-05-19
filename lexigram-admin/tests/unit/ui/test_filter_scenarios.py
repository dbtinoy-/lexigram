"""Scenario tests for combined filter+search+sort+page-size state propagation.

These tests verify that the baked state pattern (hx-vals) correctly propagates
all active state dimensions across controls when multiple are active.
"""

from lexigram.admin.ui.filters.types import SelectFilter
from lexigram.admin.ui.molecules.filter_bar import FilterBar
from lexigram.ui import TablePagination as Pagination
from lexigram.ui.state import TableState
from lexigram.ui import render_to_string


class TestFilterCarriesCombinedState:
    """Filter controls carry all non-filter state via hx-vals."""

    def test_filter_carries_search_term(self) -> None:
        state = TableState(search="findme", filters={"status": "active"})
        fb = FilterBar(
            filters=[SelectFilter("role", options=["admin", "user"])],
            state=state,
            resource_prefix="/admin/users",
        )
        html = render_to_string(fb)
        assert "hx-vals" in html
        assert "findme" in html

    def test_filter_carries_sort(self) -> None:
        state = TableState(sort_by="name", sort_order="desc")
        fb = FilterBar(
            filters=[SelectFilter("status", options=["active", "inactive"])],
            state=state,
            resource_prefix="/admin/users",
        )
        html = render_to_string(fb)
        assert "hx-vals" in html
        assert "sort_by" in html
        assert "desc" in html

    def test_filter_carries_other_filter_value(self) -> None:
        state = TableState(filters={"status": "active"})
        fb = FilterBar(
            filters=[SelectFilter("role", options=["admin", "user"])],
            state=state,
            resource_prefix="/admin/users",
        )
        html = render_to_string(fb)
        assert "hx-vals" in html
        assert "active" in html

    def test_filter_carries_custom_page_size(self) -> None:
        state = TableState(per_page=50)
        fb = FilterBar(
            filters=[SelectFilter("role", options=["admin", "user"])],
            state=state,
            resource_prefix="/admin/users",
        )
        html = render_to_string(fb)
        assert "hx-vals" in html
        assert "50" in html

    def test_multiple_filters_each_has_full_state(self) -> None:
        state = TableState(
            search="test",
            sort_by="name",
            sort_order="desc",
            filters={"status": "active", "role": "admin"},
            per_page=50,
        )
        fb = FilterBar(
            filters=[
                SelectFilter("status", options=["active", "inactive"]),
                SelectFilter("role", options=["admin", "user"]),
            ],
            state=state,
            resource_prefix="/admin/users",
        )
        html = render_to_string(fb)
        assert "hx-vals" in html
        assert "desc" in html
        assert "50" in html


class TestPaginationCarriesCombinedState:
    """Pagination controls carry all filter/search/sort state."""

    def test_page_links_carry_filter_and_search(self) -> None:
        state = TableState(page=2, filters={"status": "active"}, search="findme")
        pag = Pagination(total=50, base_url="/admin/users", state=state)
        html = render_to_string(pag)
        assert "active" in html
        assert "findme" in html

    def test_size_selector_carries_filters(self) -> None:
        state = TableState(
            filters={"status": "active"}, search="findme", sort_by="name"
        )
        pag = Pagination(total=50, base_url="/admin/users", state=state)
        html = render_to_string(pag)
        assert "hx-vals" in html
        assert "active" in html
        assert "findme" in html

    def test_page_links_carry_include_deleted(self) -> None:
        state = TableState(include_deleted=True, sort_by="name")
        pag = Pagination(total=50, base_url="/admin/users", state=state)
        html = render_to_string(pag)
        assert "include_deleted" in html or "true" in html
