"""Sortable column header rendering contract.

Sortable headers must expose a real, focusable ``<button type="button">``
inside the ``<th>`` carrying the HTMX attributes (a plain clickable ``<th>``
is not keyboard reachable), and the header cell must announce the current
sort state with ``aria-sort``.
"""

from __future__ import annotations

import re

from lexigram.ui.columns.types import TextColumn
from lexigram.ui.state import TableState


class TestSortableHeader:
    def test_sortable_header_renders_button_with_htmx_and_aria_sort(
        self,
    ) -> None:
        col = TextColumn("email", "Email").sortable(True)
        state = TableState(sort_by="email", sort_order="asc")
        header = col.render_header(
            "email",
            "asc",
            state=state,
            resource_prefix="/admin/users",
        )
        html = str(header)

        # th announces the sort state; the button carries the interaction.
        assert 'aria-sort="ascending"' in html
        assert re.search(r"<th[^>]*hx-get=", html) is None
        assert re.search(r"<button[^>]*type=\"button\"[^>]*hx-get=", html)

    def test_unsorted_header_aria_sort_none(self) -> None:
        col = TextColumn("name", "Name").sortable(True)
        state = TableState(sort_by="email", sort_order="asc")
        header = col.render_header(
            "email",
            "asc",
            state=state,
            resource_prefix="/admin/users",
        )
        html = str(header)
        assert 'aria-sort="none"' in html
        # Sort affordance is still a real button (hover/indicator icon renders
        # as an inline SVG, so presence of the button is the contract).
        assert re.search(r"<button[^>]*type=\"button\"[^>]*hx-get=", html)

    def test_descending_sort_aria_sort_descending(self) -> None:
        col = TextColumn("name", "Name").sortable(True)
        state = TableState(sort_by="name", sort_order="desc")
        header = col.render_header(
            "name",
            "desc",
            state=state,
            resource_prefix="/admin/users",
        )
        html = str(header)
        assert 'aria-sort="descending"' in html

    def test_non_sortable_column_has_no_button_or_aria_sort(self) -> None:
        col = TextColumn("email", "Email")
        state = TableState(sort_by="email", sort_order="asc")
        header = col.render_header(
            "email",
            "asc",
            state=state,
            resource_prefix="/admin/users",
        )
        html = str(header)
        assert "aria-sort" not in html
        assert "<button" not in html
