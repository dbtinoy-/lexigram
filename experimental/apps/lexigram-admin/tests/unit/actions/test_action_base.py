"""Tests for Action base class and specializations — RowAction, BulkAction, HeaderAction."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.result import Ok, Result
from lexigram.admin.actions.base import Action, RowAction, BulkAction, HeaderAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionColor, ActionContext


# --- Concrete subclasses for testing ---


class ConcreteRowAction(RowAction):
    """Minimal concrete RowAction for testing."""

    async def execute(
        self, record_or_records: Any, ctx: ActionContext
    ) -> Result[Any, ActionError]:
        return Ok(f"processed {record_or_records}")


class ConcreteBulkAction(BulkAction):
    """Minimal concrete BulkAction for testing."""

    async def execute(
        self, record_or_records: list[Any], ctx: ActionContext
    ) -> Result[Any, ActionError]:
        return Ok(len(record_or_records))


class ConcreteHeaderAction(HeaderAction):
    """Minimal concrete HeaderAction for testing."""

    async def execute(
        self, record_or_records: None, ctx: ActionContext
    ) -> Result[Any, ActionError]:
        return Ok("header executed")


class TestActionABC:
    """Tests for Action abstract base class."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            Action[Any, Any](name="abstract")  # type: ignore[abstract]

    def test_row_action_is_action(self) -> None:
        action = ConcreteRowAction(name="view")
        assert isinstance(action, Action)

    def test_bulk_action_is_action(self) -> None:
        action = ConcreteBulkAction(name="bulk_delete")
        assert isinstance(action, Action)

    def test_header_action_is_action(self) -> None:
        action = ConcreteHeaderAction(name="export")
        assert isinstance(action, Action)


class TestActionDefaults:
    """Tests for Action default field values."""

    def test_label_defaults_to_none(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.label is None

    def test_icon_defaults_to_none(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.icon is None

    def test_color_defaults_to_gray(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.color == ActionColor.GRAY

    def test_keyboard_shortcut_defaults_to_none(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.keyboard_shortcut is None

    def test_custom_field_values(self) -> None:
        action = ConcreteRowAction(
            name="edit",
            label="Edit",
            icon="pencil",
            color=ActionColor.PRIMARY,
            keyboard_shortcut="Ctrl+E",
        )
        assert action.name == "edit"
        assert action.label == "Edit"
        assert action.icon == "pencil"
        assert action.color == ActionColor.PRIMARY
        assert action.keyboard_shortcut == "Ctrl+E"


class TestActionLifecycleHooks:
    """Tests for Action lifecycle methods."""

    def test_visible_for_returns_true_by_default(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.visible_for("record") is True

    def test_visible_for_with_user(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.visible_for("record", user="admin") is True

    def test_authorize_returns_ok_by_default(self) -> None:
        action = ConcreteRowAction(name="test")
        result = action.authorize("record")
        assert result.is_ok()

    def test_authorize_returns_ok_with_user(self) -> None:
        action = ConcreteRowAction(name="test")
        result = action.authorize("record", user="admin")
        assert result.is_ok()

    def test_form_returns_none_by_default(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.form() is None

    def test_confirm_returns_none_by_default(self) -> None:
        action = ConcreteRowAction(name="test")
        assert action.confirm() is None


class TestActionRenderButton:
    """Tests for Action.render_button."""

    def test_render_button_returns_element(self) -> None:
        action = ConcreteRowAction(name="test", label="Test")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "123"}, ctx)
        assert isinstance(result, str)
        assert "Test" in result

    def test_render_button_inactive_without_id(self) -> None:
        action = ConcreteRowAction(name="test")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({}, ctx)
        assert result == ""

    def test_render_button_empty_without_id(self) -> None:
        action = ConcreteRowAction(name="test")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({}, ctx)
        assert result == ""

    def test_render_button_htmx_url(self) -> None:
        action = ConcreteRowAction(name="view", label="View")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "hx-get" in result
        assert "/users/42/view" in result

    def test_render_button_with_color(self) -> None:
        action = ConcreteRowAction(
            name="delete", label="Delete", icon="trash",
            color=ActionColor.DANGER,
        )
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "1"}, ctx)
        assert "Delete" in result

    def test_bulk_action_url(self) -> None:
        action = ConcreteBulkAction(name="bulk_delete")
        ctx = ActionContext(resource_name="users")
        result = action.render_button([{"id": "1"}], ctx)
        assert "/users/bulk/bulk_delete" in result

    def test_header_action_url(self) -> None:
        action = ConcreteHeaderAction(name="create")
        ctx = ActionContext(resource_name="users")
        result = action.render_button(None, ctx)
        assert "/users/create" in result


class TestActionExecute:
    """Tests for Action.execute."""

    @pytest.mark.asyncio
    async def test_row_action_execute(self) -> None:
        action = ConcreteRowAction(name="view")
        ctx = ActionContext(resource_name="users")
        result = await action.execute("record-1", ctx)
        assert result.is_ok()
        assert result.unwrap() == "processed record-1"

    @pytest.mark.asyncio
    async def test_bulk_action_execute(self) -> None:
        action = ConcreteBulkAction(name="bulk_delete")
        ctx = ActionContext(resource_name="users")
        result = await action.execute(["a", "b", "c"], ctx)
        assert result.is_ok()
        assert result.unwrap() == 3

    @pytest.mark.asyncio
    async def test_header_action_execute(self) -> None:
        action = ConcreteHeaderAction(name="export")
        ctx = ActionContext(resource_name="reports")
        result = await action.execute(None, ctx)
        assert result.is_ok()
        assert result.unwrap() == "header executed"


class TestActionSpecializations:
    """Tests for RowAction, BulkAction, HeaderAction classes."""

    def test_row_action_is_action_subclass(self) -> None:
        assert issubclass(RowAction, Action)

    def test_bulk_action_is_action_subclass(self) -> None:
        assert issubclass(BulkAction, Action)

    def test_header_action_is_action_subclass(self) -> None:
        assert issubclass(HeaderAction, Action)
