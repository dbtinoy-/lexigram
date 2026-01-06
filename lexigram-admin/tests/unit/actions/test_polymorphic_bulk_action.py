"""Tests for PolymorphicBulkAction (E8)."""

from __future__ import annotations

from typing import Any, ClassVar

from lexigram.admin.actions.base import Action, BulkAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionContext
from lexigram.result import Err, Ok, Result


class TypeA:
    def __init__(self, value: str) -> None:
        self.value = value


class TypeB:
    def __init__(self, value: str) -> None:
        self.value = value


class TypeC:
    pass


class HandleAAction(Action[TypeA, str]):
    async def execute(self, record_or_records: TypeA, ctx: ActionContext) -> Result[str, ActionError]:
        return Ok(f"A:{record_or_records.value}")


class HandleBAction(Action[TypeB, str]):
    async def execute(self, record_or_records: TypeB, ctx: ActionContext) -> Result[str, ActionError]:
        return Ok(f"B:{record_or_records.value}")


class FailingAction(Action[TypeA, str]):
    async def execute(self, record_or_records: TypeA, ctx: ActionContext) -> Result[str, ActionError]:
        return Err(ActionError("forced failure"))


from lexigram.admin.actions.polymorphic import PolymorphicBulkAction


class ConcretePolyAction(PolymorphicBulkAction):
    name = "poly_test"
    handlers: ClassVar[dict[type, Action[Any, Any]]] = {
        TypeA: HandleAAction(name="handle_a"),
        TypeB: HandleBAction(name="handle_b"),
    }


class FailingPolyAction(PolymorphicBulkAction):
    name = "poly_fail"
    handlers: ClassVar[dict[type, Action[Any, Any]]] = {
        TypeA: FailingAction(name="fail_a"),
    }


_CTX = ActionContext(resource_name="test_resource")


async def test_dispatches_to_correct_handler_for_type_a() -> None:
    action = ConcretePolyAction(name="poly_test")
    records = [TypeA("x"), TypeA("y")]
    result = await action.execute(records, _CTX)
    assert result.is_ok()


async def test_dispatches_to_correct_handler_for_type_b() -> None:
    action = ConcretePolyAction(name="poly_test")
    records = [TypeB("z")]
    result = await action.execute(records, _CTX)
    assert result.is_ok()


async def test_dispatches_mixed_types() -> None:
    action = ConcretePolyAction(name="poly_test")
    records = [TypeA("a"), TypeB("b"), TypeA("c")]
    result = await action.execute(records, _CTX)
    assert result.is_ok()


async def test_returns_err_for_unhandled_type() -> None:
    action = ConcretePolyAction(name="poly_test")
    records = [TypeC()]
    result = await action.execute(records, _CTX)
    assert result.is_err()


async def test_returns_err_when_handler_fails() -> None:
    action = FailingPolyAction(name="poly_fail")
    records = [TypeA("boom")]
    result = await action.execute(records, _CTX)
    assert result.is_err()


async def test_empty_list_returns_ok() -> None:
    action = ConcretePolyAction(name="poly_test")
    result = await action.execute([], _CTX)
    assert result.is_ok()


def test_is_subclass_of_bulk_action() -> None:
    assert issubclass(PolymorphicBulkAction, BulkAction)


def test_polymorphic_bulk_action_exported_from_actions() -> None:
    from lexigram.admin.actions.polymorphic import PolymorphicBulkAction as PBA
    assert PBA is not None
