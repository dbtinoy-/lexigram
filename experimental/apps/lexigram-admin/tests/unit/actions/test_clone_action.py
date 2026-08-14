"""Tests for CloneAction implementation."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.actions.base import Action, RowAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.standard import CloneAction
from lexigram.admin.actions.types import ActionColor, ActionContext


class TestCloneAction:
    """Tests for CloneAction."""

    def test_default_name(self) -> None:
        action = CloneAction()
        assert action.name == "clone"

    def test_default_label(self) -> None:
        action = CloneAction()
        assert action.label == "Clone"

    def test_icon(self) -> None:
        action = CloneAction()
        assert action.icon == "copy"

    def test_color_is_secondary(self) -> None:
        action = CloneAction()
        assert action.color == ActionColor.SECONDARY

    def test_is_row_action(self) -> None:
        action = CloneAction()
        assert isinstance(action, RowAction)
        assert isinstance(action, Action)

    def test_custom_label(self) -> None:
        action = CloneAction(label="Copy")
        assert action.label == "Copy"

    @pytest.mark.asyncio
    async def test_execute_returns_err_without_data_source(self) -> None:
        action = CloneAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": 1}, ctx)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)

    @pytest.mark.asyncio
    async def test_execute_returns_err_without_record_id(self) -> None:
        class FakeDataSource:
            async def find_one(self, item_id: Any) -> dict:
                return {"id": item_id, "name": "test"}

            async def create(self, data: dict) -> dict:
                return {"id": "new-1", **data}

        action = CloneAction(data_source=FakeDataSource())
        ctx = ActionContext(resource_name="users")
        result = await action.execute({}, ctx)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)
