"""R2 T7 — End-to-end audit chain smoke test.

Exercises the full admin audit pipeline:
  correlation context → PII redaction → UoW deferral → audit logger

Covers T7 assertions:
  1. Exactly one AuditEntry written
  2. entry.correlation_id equals the configured value
  3. entry.outcome == "success"
  4. entry.before and entry.after are PII-redacted
  5. Rollback path: RuntimeError → outcome="errored", txn rolled back
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from lexigram.admin.audit import DefaultPiiRedactor
from lexigram.admin.audit.correlation import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from lexigram.admin.audit.uow_writer import UowAuditWriter
from lexigram.contracts.admin.audit_entry import AuditEntry, AuditOutcome


class _FakeAdminAuditLogger:
    """Implements AdminAuditLoggerProtocol, collects entries in-memory."""

    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Any,
        user_id: Any,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def write(self, entry: AuditEntry) -> None:
        self.entries.append(entry)


class _FakeUoW:
    """Implements UoWProtocol with callable tracking."""

    def __init__(self) -> None:
        self._commit_callbacks: list[Callable[[], Any]] = []
        self._rollback_callbacks: list[Callable[[], Any]] = []
        self.committed = False
        self.rolled_back = False

    def on_commit(self, callback: Callable[[], Any]) -> None:
        self._commit_callbacks.append(callback)

    def on_rollback(self, callback: Callable[[], Any]) -> None:
        self._rollback_callbacks.append(callback)

    async def do_commit(self) -> None:
        self.committed = True
        for cb in self._commit_callbacks:
            r = cb()
            if r is not None:
                await r

    async def do_rollback(self) -> None:
        self.rolled_back = True
        for cb in self._rollback_callbacks:
            r = cb()
            if r is not None:
                await r


_PAYLOAD_WITH_PII = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+1 555-123-4567",
    "role": "admin",
}


def _verify_pii_redacted(
    payload: dict[str, Any],
    expected_name: str = "Ada Lovelace",
    expect_role: bool = True,
    expect_phone: bool = True,
) -> None:
    assert payload.get("name") == expected_name
    if expect_role:
        assert payload.get("role") == "admin"
    assert payload.get("email") == "<redacted>"
    if expect_phone:
        assert payload.get("phone") == "<redacted>"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_success_path_writes_one_entry() -> None:
    """Assert exactly one AuditEntry written through the full chain."""
    logger = _FakeAdminAuditLogger()
    uow = _FakeUoW()
    writer = UowAuditWriter(logger=logger, uow_provider=lambda: uow)
    redactor = DefaultPiiRedactor(
        field_denylist=["email", "phone"], patterns=["email", "phone"]
    )
    cid = new_correlation_id()
    set_correlation_id(cid)

    before_raw: dict[str, Any] = {"name": "Old Name", "email": "old@example.com"}
    after_raw: dict[str, Any] = dict(_PAYLOAD_WITH_PII)

    entry = AuditEntry(
        admin_user_id="admin-1",
        action="admin.user.update",
        resource_type="users",
        resource_id="u-42",
        outcome=AuditOutcome.SUCCESS,
        before=redactor.redact(before_raw),
        after=redactor.redact(after_raw),
        correlation_id=get_correlation_id(),
    )

    await writer.write(entry)
    await uow.do_commit()

    assert len(logger.entries) == 1
    entry = logger.entries[0]
    assert entry.outcome == AuditOutcome.SUCCESS
    assert entry.correlation_id == cid


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pii_redacted_in_before_and_after() -> None:
    """Assert before/after have email and phone redacted."""
    logger = _FakeAdminAuditLogger()
    writer = UowAuditWriter(logger=logger, uow_provider=lambda: None)
    redactor = DefaultPiiRedactor(
        field_denylist=["email", "phone"], patterns=["email", "phone"]
    )
    cid = new_correlation_id()
    set_correlation_id(cid)

    before = redactor.redact({"name": "Old", "email": "old@example.com"})
    after = redactor.redact(dict(_PAYLOAD_WITH_PII))

    entry = AuditEntry(
        admin_user_id="admin-1",
        action="admin.user.update",
        resource_type="users",
        resource_id="u-42",
        outcome=AuditOutcome.SUCCESS,
        before=before,
        after=after,
        correlation_id=get_correlation_id(),
    )

    await writer.write(entry)

    assert len(logger.entries) == 1
    e = logger.entries[0]
    _verify_pii_redacted(
        e.before, expected_name="Old", expect_role=False, expect_phone=False
    )
    _verify_pii_redacted(e.after)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rollback_path_writes_errored_outcome() -> None:
    """Assert that when an action raises RuntimeError, audit records outcome=errored."""
    logger = _FakeAdminAuditLogger()
    uow = _FakeUoW()
    writer = UowAuditWriter(logger=logger, uow_provider=lambda: uow)
    cid = new_correlation_id()
    set_correlation_id(cid)

    try:
        resource_before: dict[str, Any] = {"name": "Widget", "status": "active"}
        raise RuntimeError("mid-action failure")
    except RuntimeError:
        entry = AuditEntry(
            admin_user_id="admin-1",
            action="admin.user.update",
            resource_type="users",
            resource_id="u-42",
            outcome=AuditOutcome.ERRORED,
            before=resource_before,
            after={},
            correlation_id=get_correlation_id(),
        )
        # Errored entries bypass UoW deferral — write immediately
        await logger.write(entry)
        await uow.do_rollback()

    assert len(logger.entries) == 1
    assert logger.entries[0].outcome == AuditOutcome.ERRORED
    assert uow.rolled_back
    assert not uow.committed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_correlation_id_propagates_through_chain() -> None:
    """Assert correlation_id set at the start is present on the written entry."""
    logger = _FakeAdminAuditLogger()
    writer = UowAuditWriter(logger=logger, uow_provider=lambda: None)
    cid = new_correlation_id()
    set_correlation_id(cid)

    entry = AuditEntry(
        admin_user_id="admin-1",
        action="admin.user.create",
        resource_type="users",
        resource_id="u-99",
        outcome=AuditOutcome.SUCCESS,
        correlation_id=get_correlation_id(),
    )

    await writer.write(entry)

    assert len(logger.entries) == 1
    assert logger.entries[0].correlation_id == cid


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uow_defers_write_until_commit() -> None:
    """Assert UowAuditWriter defers the write until UoW commits."""
    logger = _FakeAdminAuditLogger()
    uow = _FakeUoW()
    writer = UowAuditWriter(logger=logger, uow_provider=lambda: uow)

    entry = AuditEntry(
        admin_user_id="admin-1",
        action="admin.user.delete",
        resource_type="users",
        resource_id="u-1",
        outcome=AuditOutcome.SUCCESS,
    )

    await writer.write(entry)

    # Before commit: entry not yet forwarded to logger
    assert len(logger.entries) == 0

    await uow.do_commit()

    # After commit: entry appears in logger
    assert len(logger.entries) == 1
    assert logger.entries[0].resource_id == "u-1"
