"""Tests for row manager types."""

import pytest

from lexigram.admin.actions.row_manager.types import (
    ActionPosition,
    ActionStyle,
    RowAction,
)


class TestActionStyle:
    """Tests for ActionStyle enum."""

    def test_action_style_values(self) -> None:
        """Test ActionStyle enum values."""
        assert ActionStyle.PRIMARY.value == "primary"
        assert ActionStyle.SECONDARY.value == "secondary"
        assert ActionStyle.SUCCESS.value == "success"
        assert ActionStyle.DANGER.value == "danger"
        assert ActionStyle.WARNING.value == "warning"
        assert ActionStyle.INFO.value == "info"

    def test_action_style_members(self) -> None:
        """Test ActionStyle has expected members."""
        members = list(ActionStyle)
        assert len(members) == 6


class TestActionPosition:
    """Tests for ActionPosition enum."""

    def test_action_position_values(self) -> None:
        """Test ActionPosition enum values."""
        assert ActionPosition.ROW_START.value == "row_start"
        assert ActionPosition.ROW_END.value == "row_end"
        assert ActionPosition.DROPDOWN.value == "dropdown"

    def test_action_position_members(self) -> None:
        """Test ActionPosition has expected members."""
        members = list(ActionPosition)
        assert len(members) == 3


class TestRowAction:
    """Tests for RowAction dataclass."""

    def test_row_action_defaults(self) -> None:
        """Test RowAction default values."""
        action = RowAction(name="edit", label="Edit")
        assert action.name == "edit"
        assert action.label == "Edit"
        assert action.handler is None
        assert action.icon is None
        assert action.style == ActionStyle.SECONDARY
        assert action.position == ActionPosition.ROW_END
        assert action.confirm is False

    def test_row_action_with_options(self) -> None:
        """Test RowAction with options."""
        action = RowAction(
            name="delete",
            label="Delete",
            icon="trash",
            style=ActionStyle.DANGER,
            position=ActionPosition.DROPDOWN,
            confirm=True,
            confirm_message="Are you sure?",
        )
        assert action.icon == "trash"
        assert action.style == ActionStyle.DANGER
        assert action.position == ActionPosition.DROPDOWN
        assert action.confirm is True
        assert action.confirm_message == "Are you sure?"
