"""Tests for TableState.with_group_by and the GroupBySwitcher molecule."""

from lexigram.ui.core.base import render_to_string
from lexigram.ui.columns.types import TextColumn
from lexigram.ui.molecules.group_by_switcher import GroupBySwitcher
from lexigram.ui.state import TableState


def test_with_group_by_sets_column():
    state = TableState()
    updated = state.with_group_by("role")
    assert updated.group_by == "role"
    assert state.group_by is None  # immutability


def test_with_group_by_none_clears():
    state = TableState(group_by="role")
    updated = state.with_group_by(None)
    assert updated.group_by is None


def test_with_group_by_resets_page():
    state = TableState(page=3)
    updated = state.with_group_by("role")
    assert updated.page == 1


def test_group_by_switcher_lists_columns_and_no_grouping():
    cols = [TextColumn("name"), TextColumn("role")]
    switcher = GroupBySwitcher(
        current=None,
        resource_prefix="/admin/users",
        columns=cols,
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "Group by" in html
    assert "No grouping" in html
    assert "Role" in html
    assert "Name" in html


def test_group_by_switcher_marks_current_selection():
    cols = [TextColumn("name"), TextColumn("role")]
    switcher = GroupBySwitcher(
        current="role",
        resource_prefix="/admin/users",
        columns=cols,
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "Group by: Role" in html
    assert "aria-current" in html


def test_group_by_switcher_emits_group_by_param():
    cols = [TextColumn("name"), TextColumn("role")]
    switcher = GroupBySwitcher(
        current=None,
        resource_prefix="/admin/users",
        columns=cols,
        state=TableState(),
    )
    html = render_to_string(switcher)
    assert "group_by=name" in html
    assert "group_by=role" in html