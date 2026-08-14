"""Tests for AuditedAction base class (S3)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.actions.audited import AuditedAction
from lexigram.admin.actions.base import Action, RowAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionContext
from lexigram.contracts.admin.audit_entry import AuditEntry, AuditOutcome
from lexigram.result import Err, Ok, Result


class _FakeAuditWriter:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    async def write(self, entry: AuditEntry) -> None:
        self.entries.append(entry)


class _ConcreteAudited(AuditedAction[dict, str], RowAction):
    """Minimal concrete AuditedAction for testing.

    Must also inherit RowAction (or another Action subclass) to provide
    the abstract `execute` implementation supplied by AuditedAction.
    """

    name: str = "test_action"
    label: str | None = "Test"
    resource_type: str = "users"

    async def execute_audited(
        self, record: dict, ctx: ActionContext
    ) -> Result[str, ActionError]:
        return Ok("done")


class _FailingAudited(AuditedAction[dict, str], RowAction):
    name: str = "fail_action"
    resource_type: str = "users"

    async def execute_audited(
        self, record: dict, ctx: ActionContext
    ) -> Result[str, ActionError]:
        return Err(ActionError("boom"))


class TestAuditedActionHierarchy:
    def test_is_subclass_of_action(self) -> None:
        assert issubclass(_ConcreteAudited, Action)

    def test_is_subclass_of_row_action(self) -> None:
        assert issubclass(_ConcreteAudited, RowAction)

    def test_instance_is_action(self) -> None:
        action = _ConcreteAudited(name="test_action")
        assert isinstance(action, Action)


class TestAuditedActionWrites:
    async def test_writes_entry_on_success(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(
            user=type("U", (), {"user_id": "u-1"})(),
            resource_name="users",
            audit_writer=writer,
        )
        action = _ConcreteAudited(name="test_action")
        result = await action.execute({"id": "r-1"}, ctx)

        assert result.is_ok()
        assert len(writer.entries) == 1
        entry = writer.entries[0]
        assert entry.outcome == AuditOutcome.SUCCESS
        assert entry.action == "test_action"
        assert entry.resource_type == "users"

    async def test_writes_errored_entry_on_failure(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(
            user=type("U", (), {"user_id": "u-1"})(),
            resource_name="users",
            audit_writer=writer,
        )
        action = _FailingAudited(name="fail_action")
        result = await action.execute({"id": "r-1"}, ctx)

        assert result.is_err()
        assert len(writer.entries) == 1
        assert writer.entries[0].outcome == AuditOutcome.ERRORED

    async def test_no_writer_does_not_raise(self) -> None:
        ctx = ActionContext(resource_name="users")  # audit_writer=None
        action = _ConcreteAudited(name="test_action")
        result = await action.execute({"id": "r-1"}, ctx)
        assert result.is_ok()

    async def test_admin_user_id_from_ctx_user(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(
            user=type("U", (), {"user_id": "admin-99"})(),
            audit_writer=writer,
        )
        action = _ConcreteAudited(name="test_action")
        await action.execute({"id": "r-1"}, ctx)

        assert writer.entries[0].admin_user_id == "admin-99"

    async def test_resource_id_extracted_from_record(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(audit_writer=writer)
        action = _ConcreteAudited(name="test_action")
        await action.execute({"id": "item-7"}, ctx)

        assert writer.entries[0].resource_id == "item-7"

    async def test_ctx_record_id_overrides_extracted_id(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(audit_writer=writer, record_id="explicit-id")
        action = _ConcreteAudited(name="test_action")
        await action.execute({"id": "item-7"}, ctx)

        assert writer.entries[0].resource_id == "explicit-id"

    async def test_ctx_metadata_included_in_entry(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(audit_writer=writer, metadata={"reason": "test-run"})
        action = _ConcreteAudited(name="test_action")
        await action.execute({}, ctx)

        assert writer.entries[0].metadata["reason"] == "test-run"

    async def test_correlation_id_propagated(self) -> None:
        writer = _FakeAuditWriter()
        ctx = ActionContext(audit_writer=writer, correlation_id="cid-42")
        action = _ConcreteAudited(name="test_action")
        await action.execute({}, ctx)

        assert writer.entries[0].correlation_id == "cid-42"


class TestCaptureHooks:
    async def test_before_and_after_in_entry(self) -> None:
        class _WithCapture(AuditedAction[dict, str], RowAction):
            name: str = "capture_action"
            resource_type: str = "items"

            async def execute_audited(
                self, record: dict, ctx: ActionContext
            ) -> Result[str, ActionError]:
                return Ok("ok")

            def capture_before(self, record: dict) -> dict[str, Any] | None:
                return {"status": record.get("status")}

            def capture_after(self, record: dict, outcome: str) -> dict[str, Any] | None:
                return {"outcome": outcome}

        writer = _FakeAuditWriter()
        ctx = ActionContext(audit_writer=writer)
        action = _WithCapture(name="capture_action")
        await action.execute({"status": "active"}, ctx)

        entry = writer.entries[0]
        assert entry.before == {"status": "active"}
        assert entry.after == {"outcome": "ok"}
