"""Tests for the DensitySwitcher molecule."""

from __future__ import annotations

from lexigram.ui.core.base import render_to_string
from lexigram.ui.molecules.density_switcher import DensitySwitcher
from lexigram.ui.state import TableState


def test_renders_three_density_options() -> None:
    switcher = DensitySwitcher(
        current="normal",
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "Compact rows" in html
    assert "Normal rows" in html
    assert "Comfortable rows" in html


def test_active_option_is_marked_pressed_and_disabled() -> None:
    switcher = DensitySwitcher(
        current="compact",
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert 'aria-pressed="true"' in html
    assert "pointer-events-none" in html


def test_inactive_options_emit_density_param() -> None:
    switcher = DensitySwitcher(
        current="normal",
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "density=compact" in html
    assert "density=comfortable" in html
    # Current option must not navigate
    assert "density=normal" not in html


def test_preserves_existing_state_in_url() -> None:
    state = TableState(search="bob", sort_by="name", page=3)
    switcher = DensitySwitcher(
        current="normal",
        resource_prefix="/admin/users",
        state=state,
    )
    html = render_to_string(switcher)
    assert "search=bob" in html
    assert "sort_by=name" in html
    assert "page=3" in html


def test_invalid_current_falls_back_to_normal() -> None:
    switcher = DensitySwitcher(
        current="huge",
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "density=compact" in html
    assert "density=comfortable" in html


def test_renders_marker_for_server_side_detection() -> None:
    switcher = DensitySwitcher(
        current="normal",
        resource_prefix="/admin/users",
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "density-switcher" in html
