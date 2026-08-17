"""Tests for standard action implementations — EditAction, ViewAction, DeleteAction, CreateAction, DeleteBulkAction."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.result import Ok, Result
from lexigram.admin.actions.base import Action, BulkAction, HeaderAction, RowAction
from lexigram.admin.actions.standard import (
    CreateAction,
    DeleteAction,
    DeleteBulkAction,
    EditAction,
    ViewAction,
)
from lexigram.admin.actions.types import ActionColor, ActionContext, ConfirmationConfig


class TestEditAction:
    """Tests for EditAction."""

    def test_default_name(self) -> None:
        action = EditAction()
        assert action.name == "edit"

    def test_default_label(self) -> None:
        action = EditAction()
        assert action.label == "Edit"

    def test_icon(self) -> None:
        action = EditAction()
        assert action.icon == "pencil"

    def test_color_is_primary(self) -> None:
        action = EditAction()
        assert action.color == ActionColor.PRIMARY

    def test_is_row_action(self) -> None:
        action = EditAction()
        assert isinstance(action, RowAction)
        assert isinstance(action, Action)

    def test_custom_name_and_label(self) -> None:
        action = EditAction(name="modify", label="Modify")
        assert action.name == "modify"
        assert action.label == "Modify"

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self) -> None:
        action = EditAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": 1}, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert isinstance(value, dict)
        assert "Edited" in value["message"]


class TestViewAction:
    """Tests for ViewAction."""

    def test_default_name(self) -> None:
        action = ViewAction()
        assert action.name == "view"

    def test_default_label(self) -> None:
        action = ViewAction()
        assert action.label == "View"

    def test_icon(self) -> None:
        action = ViewAction()
        assert action.icon == "eye"

    def test_color_is_gray(self) -> None:
        action = ViewAction()
        assert action.color == ActionColor.GRAY

    def test_is_row_action(self) -> None:
        action = ViewAction()
        assert isinstance(action, RowAction)
        assert isinstance(action, Action)

    def test_custom_name_and_label(self) -> None:
        action = ViewAction(name="preview", label="Preview")
        assert action.name == "preview"
        assert action.label == "Preview"

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self) -> None:
        action = ViewAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": 1}, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert isinstance(value, dict)
        assert "Viewed" in value["message"]


class TestDeleteAction:
    """Tests for DeleteAction."""

    def test_default_name(self) -> None:
        action = DeleteAction()
        assert action.name == "delete"

    def test_default_label(self) -> None:
        action = DeleteAction()
        assert action.label == "Delete"

    def test_icon(self) -> None:
        action = DeleteAction()
        assert action.icon == "trash"

    def test_color_is_danger(self) -> None:
        action = DeleteAction()
        assert action.color == ActionColor.DANGER

    def test_is_row_action(self) -> None:
        action = DeleteAction()
        assert isinstance(action, RowAction)
        assert isinstance(action, Action)

    def test_confirm_returns_config(self) -> None:
        action = DeleteAction()
        config = action.confirm()
        assert isinstance(config, ConfirmationConfig)
        assert config.title == "Delete Record"
        assert "Are you sure" in (config.message or "")
        assert config.style == ActionColor.DANGER

    def test_custom_confirm_title_and_message(self) -> None:
        action = DeleteAction(
            name="remove",
            label="Remove",
            confirm_title="Remove Entry",
            confirm_message="Permanently remove this entry?",
        )
        assert action.name == "remove"
        assert action.label == "Remove"
        config = action.confirm()
        assert config is not None
        assert config.title == "Remove Entry"
        assert config.message == "Permanently remove this entry?"

    @pytest.mark.asyncio
    async def test_execute_returns_ok_with_deleted_true(self) -> None:
        action = DeleteAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute({"id": 1}, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert value["deleted"] is True
        assert "Deleted" in value["message"]


class TestCreateAction:
    """Tests for CreateAction."""

    def test_default_name(self) -> None:
        action = CreateAction()
        assert action.name == "create"

    def test_default_label(self) -> None:
        action = CreateAction()
        assert action.label == "Create"

    def test_icon(self) -> None:
        action = CreateAction()
        assert action.icon == "plus"

    def test_color_is_primary(self) -> None:
        action = CreateAction()
        assert action.color == ActionColor.PRIMARY

    def test_is_header_action(self) -> None:
        action = CreateAction()
        assert isinstance(action, HeaderAction)
        assert isinstance(action, Action)
        assert not isinstance(action, RowAction)
        assert not isinstance(action, BulkAction)

    def test_custom_name_and_label(self) -> None:
        action = CreateAction(name="add", label="Add New")
        assert action.name == "add"
        assert action.label == "Add New"

    @pytest.mark.asyncio
    async def test_execute_returns_ok(self) -> None:
        action = CreateAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute(None, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert isinstance(value, dict)
        assert "Created" in value["message"]


class TestDeleteBulkAction:
    """Tests for DeleteBulkAction."""

    def test_default_name(self) -> None:
        action = DeleteBulkAction()
        assert action.name == "delete"

    def test_default_label(self) -> None:
        action = DeleteBulkAction()
        assert action.label == "Delete Selected"

    def test_icon(self) -> None:
        action = DeleteBulkAction()
        assert action.icon == "trash"

    def test_color_is_danger(self) -> None:
        action = DeleteBulkAction()
        assert action.color == ActionColor.DANGER

    def test_is_bulk_action(self) -> None:
        action = DeleteBulkAction()
        assert isinstance(action, BulkAction)
        assert isinstance(action, Action)
        assert not isinstance(action, RowAction)

    def test_confirm_returns_config(self) -> None:
        action = DeleteBulkAction()
        config = action.confirm()
        assert isinstance(config, ConfirmationConfig)
        assert config.title == "Delete Selected Records"
        assert "Are you sure" in (config.message or "")
        assert config.style == ActionColor.DANGER

    @pytest.mark.asyncio
    async def test_execute_with_records(self) -> None:
        action = DeleteBulkAction()
        ctx = ActionContext(resource_name="users")
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = await action.execute(records, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert value["deleted_count"] == 3
        assert "Deleted" in value["message"]

    @pytest.mark.asyncio
    async def test_execute_with_empty_list(self) -> None:
        action = DeleteBulkAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute([], ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert value["deleted_count"] == 0
        assert "Deleted 0 record(s)" in value["message"]
