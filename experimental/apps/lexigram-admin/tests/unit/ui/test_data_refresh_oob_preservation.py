"""Data-zone refreshes must not discard the toolbar's OOB fragments.

Sorting, searching, filtering and paginating all swap ``#table-data`` and
narrow the response with ``hx-select``. htmx implements ``hx-select`` by
rebuilding the swap from ``querySelectorAll(select)`` alone, so anything
outside the selected subtree is dropped -- including the ``hx-swap-oob``
fragments the list renderer emits for the toolbar switchers and the
Active/Trash tabs, which are siblings of ``#table-data``.

The visible result was that rows updated while every control around them
kept rendering the previous state: sort arrows pointing the wrong way,
filter chips that would not clear, and scope tabs stuck on the old view.
Pairing ``hx-select`` with ``hx-select-oob`` keeps those fragments.
"""

from __future__ import annotations

import re
from html import unescape

import pytest

from lexigram.admin.ui.organisms.data_table.coordinator import DataTable
from lexigram.ui import TableState, Zones, render_to_string
from lexigram.ui.columns.types import TextColumn

SELECT_ATTR = f'hx-select="{Zones.DATA.selector}"'


def _table(**state_kwargs: object) -> DataTable:
    return DataTable(
        columns=[TextColumn("name").sortable()],
        data=[{"name": "a"}],
        state=TableState(**state_kwargs),
        resource_prefix="/admin/users",
        total=1,
    )


def _full_render(**state_kwargs: object) -> str:
    return str(render_to_string(_table(**state_kwargs)))


def _htmx_fragment(**state_kwargs: object) -> str:
    """The response shape returned for an ``HX-Target: table-data`` request."""
    table = _table(**state_kwargs)
    table.props["htmx_request"] = True
    return str(render_to_string(table))


def _tags_with_select(html: str) -> list[str]:
    return re.findall(rf"<[^>]*{re.escape(SELECT_ATTR)}[^>]*>", html)


class TestEverySelectIsPairedWithSelectOob:
    def test_at_least_one_control_uses_hx_select(self) -> None:
        """Guards the tests below from passing vacuously."""
        assert _tags_with_select(_full_render())

    def test_no_control_narrows_the_swap_without_preserving_oob(self) -> None:
        unpaired = [
            tag for tag in _tags_with_select(_full_render()) if "hx-select-oob" not in tag
        ]

        assert unpaired == []

    @pytest.mark.parametrize(
        "state_kwargs",
        [
            {},
            {"sort_by": "name", "sort_order": "desc"},
            {"search": "alice"},
            {"filters": {"status": "active"}},
            {"include_deleted": True},
            {"page": 2},
        ],
    )
    def test_pairing_holds_across_table_states(
        self, state_kwargs: dict[str, object]
    ) -> None:
        unpaired = [
            tag
            for tag in _tags_with_select(_full_render(**state_kwargs))
            if "hx-select-oob" not in tag
        ]

        assert unpaired == []


class TestSelectorsMatchTheServerResponse:
    """A selector that matches nothing preserves nothing."""

    @pytest.mark.parametrize("selector", Zones.data_refresh_oob_select().split(","))
    def test_each_selector_is_present_in_the_htmx_fragment(
        self, selector: str
    ) -> None:
        element_id = selector.strip().lstrip("#")

        assert f'id="{element_id}"' in _htmx_fragment()

    def test_fragment_actually_marks_those_elements_oob(self) -> None:
        fragment = _htmx_fragment()

        assert fragment.count("hx-swap-oob") == len(
            Zones.data_refresh_oob_select().split(",")
        )

    def test_oob_fragments_sit_outside_the_selected_subtree(self) -> None:
        """If they were nested inside #table-data, hx-select would already
        keep them and hx-select-oob would be unnecessary -- this records why
        the pairing is required."""
        from html.parser import HTMLParser

        class _Locator(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.stack: list[str] = []
                self.nested: list[bool] = []

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                attributes = dict(attrs)
                if attributes.get("id") == Zones.DATA.id:
                    self.stack.append("DATA")
                elif tag not in ("input", "img", "br", "hr", "meta", "link"):
                    self.stack.append(tag)
                if "hx-swap-oob" in attributes:
                    self.nested.append("DATA" in self.stack)

            def handle_endtag(self, tag: str) -> None:
                if self.stack:
                    self.stack.pop()

        locator = _Locator()
        locator.feed(_htmx_fragment())

        assert locator.nested
        assert not any(locator.nested)


class TestDisabledControlsDropTheAttribute:
    """Current/disabled pagination and sort items strip their htmx attrs."""

    def test_hx_select_oob_is_stripped_alongside_hx_select(self) -> None:
        from lexigram.ui.molecules.pagination_links import PaginationLinks
        from lexigram.ui.molecules.sort_switcher import SortSwitcher

        for module in (PaginationLinks, SortSwitcher):
            source = __import__(
                module.__module__, fromlist=["__file__"]
            ).__file__
            assert source is not None
            text = open(source).read()  # noqa: SIM115, PTH123
            # Wherever hx_select is removed, hx_select_oob must go too.
            assert text.count('"hx_select_oob"') >= 1
