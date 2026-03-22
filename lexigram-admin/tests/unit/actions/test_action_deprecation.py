"""
Tests for legacy ui.actions system.

Old classes remain fully functional but no longer emit DeprecationWarning.
"""

from __future__ import annotations

import warnings

import pytest


def test_old_action_can_be_instantiated() -> None:
    """Old Action can still be instantiated."""
    from lexigram.ui.actions.base import Action

    action = Action(name="test_action")
    assert action.name == "test_action"
    assert action.label == "Test Action"


def test_old_action_icon_chain_works() -> None:
    """Old Action.icon() chain still works."""
    from lexigram.ui.actions.base import Action

    action = Action("test").icon("check")
    assert action._icon == "check"


def test_old_action_color_chain_works() -> None:
    """Old Action.color() chain still works."""
    from lexigram.ui.actions.base import Action

    action = Action("test").color("success")
    assert action._color == "success"


def test_old_action_render_returns_value() -> None:
    """Old Action.render() still returns something."""
    from lexigram.ui.actions.base import Action

    action = Action("test", label="Test")
    result = action.render()
    assert result is not None
    assert result != ""


def test_old_bulk_action_can_be_instantiated() -> None:
    """Old BulkAction can still be instantiated."""
    from lexigram.ui.actions.base import BulkAction

    action = BulkAction(name="bulk_test")
    assert action.name == "bulk_test"
    assert action._deselect_after is True


def test_old_edit_action_can_be_instantiated() -> None:
    """Old EditAction can still be instantiated."""
    from lexigram.ui.actions.standard import EditAction

    action = EditAction()
    assert action.name == "edit"
    assert action.label == "Edit"
    assert action._icon == "pencil"
    assert action._color == "primary"


def test_old_delete_action_defaults() -> None:
    """Old DeleteAction still has correct defaults."""
    from lexigram.ui.actions.standard import DeleteAction

    action = DeleteAction()
    assert action.name == "delete"
    assert action._icon == "trash"
    assert action._color == "danger"
    assert action._requires_confirmation is True


def test_old_create_action_defaults() -> None:
    """Old CreateAction still has correct defaults."""
    from lexigram.ui.actions.standard import CreateAction

    action = CreateAction()
    assert action.name == "create"
    assert action._icon == "plus"
    assert action._color == "primary"


def test_old_view_action_defaults() -> None:
    """Old ViewAction still has correct defaults."""
    from lexigram.ui.actions.standard import ViewAction

    action = ViewAction()
    assert action.name == "view"
    assert action._icon == "eye"
    assert action._color == "gray"


def test_old_export_action_defaults() -> None:
    """Old ExportAction still has correct defaults."""
    from lexigram.ui.actions.standard import ExportAction

    action = ExportAction()
    assert action.name == "export"
    assert action._icon == "download"
    assert action._color == "gray"


def test_old_delete_bulk_action_defaults() -> None:
    """Old DeleteBulkAction still has correct defaults."""
    from lexigram.ui.actions.standard import DeleteBulkAction

    action = DeleteBulkAction()
    assert action.name == "delete"
    assert action._icon == "trash"
    assert action._color == "danger"
    assert action._deselect_after is True


def test_old_export_bulk_action_defaults() -> None:
    """Old ExportBulkAction still has correct defaults."""
    from lexigram.ui.actions.standard import ExportBulkAction

    action = ExportBulkAction()
    assert action.name == "export"
    assert action._icon == "download"
    assert action._color == "gray"
    assert action._deselect_after is True


def test_danger_chain_works() -> None:
    """Old Action.danger() chain still works."""
    from lexigram.ui.actions.base import Action

    action = Action("test").danger()
    assert action._color == "danger"


def test_success_chain_works() -> None:
    """Old Action.success() chain still works."""
    from lexigram.ui.actions.base import Action

    action = Action("test").success()
    assert action._color == "success"


def test_requires_confirmation_chain_works() -> None:
    """Old Action.requires_confirmation() chain still works."""
    from lexigram.ui.actions.base import Action

    action = Action("test").requires_confirmation()
    assert action._requires_confirmation is True


def test_old_action_visible_callback_works() -> None:
    """Old Action.visible() with callable still works."""
    from lexigram.ui.actions.base import Action

    action = Action("test").visible(lambda r: r.get("active", False))
    assert callable(action._visible_callback)
    assert action._visible_callback({"active": True}) is True
    assert action._visible_callback({"active": False}) is False
