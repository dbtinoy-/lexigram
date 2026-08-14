"""Tests for admin permissions types."""

import pytest

from lexigram.admin.auth.permissions import Action


class TestAction:
    """Tests for Action enum."""

    def test_action_values(self) -> None:
        """Test Action enum values."""
        assert Action.LIST.value == "list"
        assert Action.VIEW.value == "view"
        assert Action.CREATE.value == "create"
        assert Action.UPDATE.value == "update"
        assert Action.DELETE.value == "delete"
        assert Action.EXPORT.value == "export"
        assert Action.BULK_DELETE.value == "bulk_delete"
        assert Action.BULK_UPDATE.value == "bulk_update"

    def test_action_members(self) -> None:
        """Test Action has expected members."""
        members = list(Action)
        assert len(members) == 8

    def test_action_all_actions(self) -> None:
        """Test Action.all_actions returns all actions."""
        actions = Action.all_actions()
        assert Action.LIST in actions
        assert Action.CREATE in actions
        assert Action.DELETE in actions

    def test_action_read_only(self) -> None:
        """Test Action.read_only returns read actions."""
        read_actions = Action.read_only()
        assert Action.LIST in read_actions
        assert Action.VIEW in read_actions
        assert Action.EXPORT in read_actions
        assert Action.CREATE not in read_actions

    def test_action_write(self) -> None:
        """Test Action.write returns write actions."""
        write_actions = Action.write()
        assert Action.CREATE in write_actions
        assert Action.UPDATE in write_actions
        assert Action.DELETE in write_actions
        assert Action.LIST not in write_actions
