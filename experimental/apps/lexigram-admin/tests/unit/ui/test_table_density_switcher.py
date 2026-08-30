"""Integration tests for the density switcher in the admin DataTable."""

from __future__ import annotations

from lexigram.ui.columns.types import TextColumn
from lexigram.ui import render_to_string
from lexigram.ui.state import TableState
from lexigram.admin.ui.organisms.data_table import DataTable


def _dt(state: TableState | None = None, **props) -> DataTable:
    return DataTable(
        columns=[TextColumn("name"), TextColumn("email")],
        data=[{"id": 1, "name": "Alice", "email": "a@x.io"}],
        resource_prefix="/admin/users",
        state=state,
        **props,
    )


def test_toolbar_renders_density_switcher() -> None:
    html = render_to_string(_dt())
    assert "Compact rows" in html
    assert "Normal rows" in html
    assert "Comfortable rows" in html


def test_density_links_carry_state_params() -> None:
    dt = _dt(state=TableState(search="alice", density="normal"))
    html = render_to_string(dt)
    # Switching density preserves other state (search) in the baked URL
    assert "search=alice" in html
    assert "density=compact" in html
    assert "density=comfortable" in html


def test_state_density_overrides_config_density_for_rows() -> None:
    """URL-driven density wins over the resource default for row rendering."""
    dt = _dt(state=TableState(density="compact"))
    html = render_to_string(dt)
    assert "table-density-compact" in html
    assert "height: 32px" in html


def test_config_density_default_used_when_state_normal() -> None:
    dt = _dt(state=TableState(density="comfortable"))
    html = render_to_string(dt)
    assert "table-density-comfortable" in html
    assert "height: 64px" in html


def test_density_switcher_included_in_oob_fragments() -> None:
    html = render_to_string(
        _dt(state=TableState(density="compact"), htmx_request=True)
    )
    assert "density-switcher" in html
    assert 'hx-swap-oob="outerHTML"' in html


def test_shared_resource_config_not_mutated() -> None:
    """A compact-density request must not leak into a later normal render."""
    first = render_to_string(_dt(state=TableState(density="compact")))
    second = render_to_string(_dt(state=TableState()))
    assert "table-density-compact" in first
    assert "table-density-compact" not in second
    assert "table-density-normal" in second
