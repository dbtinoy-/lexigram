"""Tests for RestoreAction and PurgeAction implementations.

Verifies default name, label, icon, color, type hierarchy, and
basic execution for both soft-delete row actions.
"""

from __future__ import annotations

import pytest

from lexigram.admin.actions.base import Action, RowAction
from lexigram.admin.actions.standard import PurgeAction, RestoreAction
from lexigram.admin.actions.types import ActionColor, ActionContext


class TestRestoreAction:
    """Tests for RestoreAction."""

    def test_default_name(self) -> None:
        action = RestoreAction()
        assert action.name == "restore"

    def test_default_label(self) -> None:
        action = RestoreAction()
        assert action.label == "Restore"

    def test_icon(self) -> None:
        action = RestoreAction()
        assert action.icon == "rotate-ccw"

    def test_color_is_success(self) -> None:
        action = RestoreAction()
        assert action.color == ActionColor.SUCCESS

    def test_is_row_action(self) -> None:
        action = RestoreAction()
        assert isinstance(action, RowAction)
        assert isinstance(action, Action)

    def test_custom_label(self) -> None:
        action = RestoreAction(label="Undelete")
        assert action.label == "Undelete"

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self) -> None:
        action = RestoreAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": 1}, ctx)
        assert result.is_ok()


class TestPurgeAction:
    """Tests for PurgeAction."""

    def test_default_name(self) -> None:
        action = PurgeAction()
        assert action.name == "purge"

    def test_default_label(self) -> None:
        action = PurgeAction()
        assert action.label == "Purge"

    def test_icon(self) -> None:
        action = PurgeAction()
        assert action.icon == "trash-2"

    def test_color_is_danger(self) -> None:
        action = PurgeAction()
        assert action.color == ActionColor.DANGER

    def test_has_confirmation(self) -> None:
        action = PurgeAction()
        config = action.confirm()
        assert config is not None

    def test_is_row_action(self) -> None:
        action = PurgeAction()
        assert isinstance(action, RowAction)
        assert isinstance(action, Action)

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self) -> None:
        action = PurgeAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": 1}, ctx)
        assert result.is_ok()
