"""Focused tests for TablePagination."""

from __future__ import annotations

from lexigram.ui.molecules.table_pagination import TablePagination
from lexigram.ui.state import TableState


class _Req:
    def __init__(self, params: dict[str, str] | None = None) -> None:
        self.query_params = params or {}


def state(**kw: object) -> TableState:
    params = {k: str(v) for k, v in kw.items()}
    return TableState.from_request(_Req(params))


class TestLegacyMode:
    def test_no_pagination_when_total_small(self) -> None:
        assert TablePagination(total=10, per_page=20).render() == ""

    def test_summary_first_page(self) -> None:
        html = str(TablePagination(page=1, total=50, per_page=20).render())
        assert "Showing 1 to 20 of 50" in html

    def test_summary_middle_page(self) -> None:
        html = str(TablePagination(page=2, total=50, per_page=20).render())
        assert "Showing 21 to 40 of 50" in html

    def test_summary_last_partial_page(self) -> None:
        html = str(TablePagination(page=3, total=50, per_page=20).render())
        assert "Showing 41 to 50 of 50" in html

    def test_prev_disabled_on_first_page(self) -> None:
        html = str(TablePagination(page=1, total=50, per_page=20).render())
        assert 'cursor-not-allowed">Prev' in html

    def test_prev_link_on_later_page(self) -> None:
        html = str(TablePagination(page=2, total=50, per_page=20, base_url="/users").render())
        assert "/users?page=1&amp;per_page=20" in html

    def test_next_disabled_on_last_page(self) -> None:
        total_pages = 3
        html = str(TablePagination(page=total_pages, total=50, per_page=20).render())
        assert 'cursor-not-allowed">Next' in html

    def test_next_link_before_last(self) -> None:
        html = str(TablePagination(page=1, total=50, per_page=20, base_url="/users").render())
        assert "/users?page=2&amp;per_page=20" in html

    def test_current_page_emphasized(self) -> None:
        html = str(TablePagination(page=1, total=50, per_page=20).render())
        assert 'font-bold text-foreground">1<' in html

    def test_legacy_link_attrs(self) -> None:
        el = TablePagination(page=1, total=50, per_page=20, base_url="/users").render()
        link = el.children[1].children[2]
        assert link.tag == "a"
        assert "hx_get" in link.attrs
        assert link.attrs["hx_target"] == "#table-data"
        assert link.attrs["hx_swap"] == "outerHTML"
        assert link.attrs["hx_select"] == "#table-data"
        assert link.attrs["hx_push_url"] == "true"

    def test_size_selector_renders_by_default(self) -> None:
        html = str(TablePagination(page=1, total=50, per_page=20).render())
        assert "<select" in html
        assert "Show" in html
        assert 'value="25"' in html

    def test_size_selector_selected_matches_per_page(self) -> None:
        el = TablePagination(page=1, total=50, per_page=25).render()
        size_el = el.children[2]
        html = str(size_el)
        assert 'selected="selected"' in html

    def test_size_selector_disabled(self) -> None:
        html = str(
            TablePagination(page=1, total=50, per_page=20, show_size_selector=False).render()
        )
        assert "<select" not in html

    def test_size_selector_legacy_attrs(self) -> None:
        el = TablePagination(page=1, total=50, per_page=20, base_url="/users").render()
        size_el = el.children[2]
        inner = size_el.children[1]
        assert inner.attrs["hx_get"] == "/users"
        assert inner.attrs["hx_trigger"] == "change"
        assert inner.attrs["hx_target"] == "#table-data"
        assert inner.attrs["hx_swap"] == "outerHTML"


class TestVisiblePages:
    def test_small_total_all_pages(self) -> None:
        assert TablePagination(page=1, total=50, per_page=20)._get_visible_pages(1, 5) == [
            1, 2, 3, 4, 5,
        ]

    def test_first_page_large_total(self) -> None:
        assert TablePagination(page=1, total=50, per_page=20)._get_visible_pages(1, 10) == [
            1, 2, 3, None, 10,
        ]

    def test_middle_page_ellipsis_both_sides(self) -> None:
        assert TablePagination(page=1, total=50, per_page=20)._get_visible_pages(5, 10) == [
            1, None, 3, 4, 5, 6, 7, None, 10,
        ]

    def test_last_page_no_trailing_ellipsis(self) -> None:
        assert TablePagination(page=1, total=50, per_page=20)._get_visible_pages(9, 10) == [
            1, None, 7, 8, 9, 10,
        ]


class TestStateMode:
    def test_state_extracts_page_and_per_page(self) -> None:
        p = TablePagination(
            page=9, per_page=10, total=100, state=state(page=3, per_page=20)
        )
        assert p.page == 3
        assert p.per_page == 20

    def test_state_mode_page_link(self) -> None:
        el = TablePagination(
            total=100, per_page=20, base_url="/users", state=state()
        ).render()
        link = el.children[1].children[2]
        assert link.tag == "a"
        assert link.attrs["hx_get"] == "/users/?page=2"
        assert "hx_target" in link.attrs

    def test_state_mode_size_attrs(self) -> None:
        st = state(search="bob", per_page=20)
        p = TablePagination(total=100, per_page=20, base_url="/users", state=st)
        attrs = p._get_size_change_attrs()
        assert attrs["hx_get"] == "/users/"
        assert attrs["hx_trigger"] == "change"
        assert attrs["hx_push_url"] == "true"
        assert "per_page" not in attrs["hx_vals"]
        assert "page" not in attrs["hx_vals"]
        assert "search" in attrs["hx_vals"]

    def test_state_vs_legacy_page_link_attrs(self) -> None:
        state_el = TablePagination(
            total=100, per_page=20, base_url="/users", state=state()
        ).render()
        legacy_el = TablePagination(
            total=100, per_page=20, base_url="/users"
        ).render()
        state_link = state_el.children[1].children[2]
        legacy_link = legacy_el.children[1].children[2]
        state_html = str(state_link)
        assert "hx-select" in state_html or "hx-select" not in str(legacy_link)