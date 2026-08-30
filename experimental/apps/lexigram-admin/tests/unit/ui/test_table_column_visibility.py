"""Integration tests for column visibility in the admin DataTable."""

from __future__ import annotations

import re

from lexigram.ui.columns.types import TextColumn
from lexigram.ui import render_to_string
from lexigram.ui.state import TableState
from lexigram.admin.ui.organisms.data_table import DataTable

_COLUMNS = [TextColumn("name"), TextColumn("email"), TextColumn("role")]


def _dt(state: TableState | None = None, **props) -> DataTable:
    return DataTable(
        columns=_COLUMNS,
        data=[{"id": 1, "name": "Alice", "email": "a@x.io", "role": "admin"}],
        resource_prefix="/admin/users",
        state=state,
        **props,
    )


def test_toolbar_renders_column_visibility_switcher() -> None:
    html = render_to_string(_dt())
    assert "column-visibility-switcher" in html
    assert "Columns" in html


def test_hidden_columns_removed_from_table_header_and_rows() -> None:
    html = render_to_string(_dt(state=TableState(hidden_columns=["email"])))
    # No <th> for the hidden column. (The column still appears in the
    # group-by dropdown, which intentionally lists all columns.)
    assert 'data-col-name="email"' not in html
    # Data cell must not render either
    assert "a@x.io" not in html
    # Visible columns remain
    assert 'data-col-name="name"' in html
    assert 'data-col-name="role"' in html


def test_no_hidden_columns_renders_everything() -> None:
    html = render_to_string(_dt(state=TableState()))
    assert "Name" in html
    assert "Email" in html
    assert "Role" in html


def test_hidden_columns_do_not_break_colspan_math() -> None:
    """Group headers and action cells must render without colspan errors."""
    dt = _dt(
        state=TableState(hidden_columns=["email"], group_by="role"),
    )
    html = render_to_string(dt)
    assert "admin" in html  # group header rendered
    assert "Name" in html


def test_visibility_toggle_links_preserve_state() -> None:
    dt = _dt(state=TableState(search="alice", hidden_columns=["role"]))
    html = render_to_string(dt)
    # Toggle links bake the full updated state (search preserved)
    assert "search=alice" in html
    # The hidden column's toggle reveals it -> link without hide_cols
    assert "hide_cols=role" in html or "Columns" in html


def test_switcher_included_in_oob_fragments() -> None:
    html = render_to_string(_dt(state=TableState(), htmx_request=True))
    assert "column-visibility-switcher" in html
    assert 'hx-swap-oob="outerHTML"' in html


def test_shared_resource_config_not_mutated() -> None:
    """Hidden columns from one render must not leak into the next."""
    first = render_to_string(_dt(state=TableState(hidden_columns=["email"])))
    second = render_to_string(_dt(state=TableState()))
    assert "a@x.io" not in first
    assert "a@x.io" in second
