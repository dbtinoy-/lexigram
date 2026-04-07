"""Tests for TableControlFragments OOB rendering."""
from __future__ import annotations

from lexigram.admin.ui.columns.types import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.ui.core.base import render_to_string


def test_htmx_request_emits_switchers_oob() -> None:
    """When htmx_request=True, the response includes hx-swap-oob on toolbar switchers."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1, "name": "Alice"}],
        resource_prefix="/admin/users",
        htmx_request=True,
    )
    html = render_to_string(dt)
    assert 'hx-swap-oob="outerHTML"' in html
    assert "table-toolbar-switchers" in html


def test_htmx_request_emits_scope_tabs_oob() -> None:
    """When htmx_request=True, the response includes scope tabs as an OOB fragment."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1, "name": "Alice"}],
        resource_prefix="/admin/users",
        htmx_request=True,
        enable_search=True,
    )
    html = render_to_string(dt)
    # Scope tabs should be rendered as an OOB element
    assert 'id="table-scope-tabs"' in html
    assert 'hx-swap-oob="outerHTML"' in html


def test_no_oob_without_htmx_flag() -> None:
    """When htmx_request is not set, no hx-swap-oob appears in the table output."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1, "name": "Alice"}],
        resource_prefix="/admin/users",
    )
    html = render_to_string(dt)
    assert 'hx-swap-oob="outerHTML"' not in html


def test_htmx_request_contains_data_zone() -> None:
    """htmx_request=True response still contains the #table-data target zone."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1, "name": "Alice"}],
        resource_prefix="/admin/users",
        htmx_request=True,
    )
    html = render_to_string(dt)
    assert 'id="table-data"' in html


def test_htmx_request_reflects_layout_state() -> None:
    """OOB switchers reflect the current layout/view state."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1, "name": "Alice"}],
        resource_prefix="/admin/users",
        layout_type="sidebar",
        data_view="tabular",
        htmx_request=True,
    )
    html = render_to_string(dt)
    assert 'hx-swap-oob="outerHTML"' in html


def test_htmx_request_includes_clear_button_oob() -> None:
    """Clear button is included in OOB switchers fragment."""
    dt = DataTable(
        columns=[TextColumn("name")],
        data=[{"id": 1, "name": "Alice"}],
        resource_prefix="/admin/users",
        enable_search=True,
        htmx_request=True,
    )
    html = render_to_string(dt)
    assert "Clear" in html
