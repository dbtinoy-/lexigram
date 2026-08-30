"""Tests for TableState sort helpers and the SortSwitcher molecule."""

from __future__ import annotations

from lexigram.ui.columns.types import TextColumn
from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.sort_switcher import SortSwitcher
from lexigram.ui.state import TableState


def test_sort_switcher_lists_sortable_columns() -> None:
    cols = [
        TextColumn("name").sortable(),
        TextColumn("email").sortable(),
        TextColumn("secret"),
    ]
    html = render_to_string(
        SortSwitcher(
            current=None,
            resource_prefix="/admin/users",
            columns=cols,
            state=TableState(),
        )
    )
    assert "sort-switcher" in html
    assert "No sorting" in html
    assert "Name" in html
    assert "Email" in html
    assert "Secret" not in html


def test_sort_switcher_omitted_without_sortable_columns() -> None:
    html = render_to_string(
        SortSwitcher(
            resource_prefix="/admin/users",
            columns=[TextColumn("name")],
            state=TableState(),
        )
    )
    assert html == ""


def test_sort_switcher_bakes_sort_into_data_refresh() -> None:
    html = render_to_string(
        SortSwitcher(
            current=None,
            resource_prefix="/admin/users",
            columns=[TextColumn("name").sortable()],
            state=TableState(search="alice"),
        )
    )
    assert "sort_by=name" in html
    assert "search=alice" in html
    assert 'hx-target="#table-data"' in html


def test_sort_switcher_marks_current_column() -> None:
    html = render_to_string(
        SortSwitcher(
            current="name",
            current_order="asc",
            resource_prefix="/admin/users",
            columns=[TextColumn("name").sortable()],
            state=TableState(sort_by="name", sort_order="asc"),
        )
    )
    assert "Sort: Name ↑" in html
    assert "aria-current" in html
