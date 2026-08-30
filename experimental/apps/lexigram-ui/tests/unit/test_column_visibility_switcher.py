"""Tests for the ColumnVisibilitySwitcher molecule."""

from __future__ import annotations

from lexigram.ui.columns.types import TextColumn
from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.column_visibility_switcher import (
    ColumnVisibilitySwitcher,
)
from lexigram.ui.state import TableState


def _columns() -> list[TextColumn]:
    return [TextColumn("name"), TextColumn("email"), TextColumn("role")]


def test_lists_all_columns() -> None:
    switcher = ColumnVisibilitySwitcher(
        columns=_columns(),
        current_hidden=[],
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "Name" in html
    assert "Email" in html
    assert "Role" in html


def test_visible_columns_checked_hidden_unchecked() -> None:
    switcher = ColumnVisibilitySwitcher(
        columns=_columns(),
        current_hidden=["email"],
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    # Visible columns report aria-checked=true, hidden one false
    assert 'aria-checked="true"' in html
    assert 'aria-checked="false"' in html
    # Hidden column shows the empty-box indicator, visible one the check
    assert 'class="h-4 w-4 inline-block border' in html


def test_toggle_links_carry_hide_cols_param() -> None:
    switcher = ColumnVisibilitySwitcher(
        columns=_columns(),
        current_hidden=["email"],
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    # Toggling a visible column hides it -> hide_cols=email
    assert "hide_cols=email" in html
    # Toggling the hidden column reveals it -> no hide_cols on that link
    assert "hide_cols=email,role" not in html
    assert "hide_cols=role" in html


def test_preserves_existing_state_in_url() -> None:
    state = TableState(search="bob", sort_by="name")
    switcher = ColumnVisibilitySwitcher(
        columns=_columns(),
        current_hidden=[],
        resource_prefix="/admin/users",
        state=state,
    )
    html = render_to_string(switcher)
    assert "search=bob" in html
    assert "sort_by=name" in html


def test_trigger_shows_hidden_count() -> None:
    switcher = ColumnVisibilitySwitcher(
        columns=_columns(),
        current_hidden=["email", "role"],
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "2 hidden" in html


def test_plain_string_columns_supported() -> None:
    switcher = ColumnVisibilitySwitcher(
        columns=["name", "email"],
        current_hidden=[],
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "Name" in html
    assert "Email" in html


def test_renders_marker_for_server_side_detection() -> None:
    switcher = ColumnVisibilitySwitcher(
        columns=_columns(),
        current_hidden=[],
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "column-visibility-switcher" in html
