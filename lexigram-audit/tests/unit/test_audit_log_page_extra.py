"""Focused tests for the audit log admin page and helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from lexigram.audit.admin.pages.audit_log import (
    AuditLogPage,
    _paging,
    _pagination_block,
    _query_int,
)
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity
from lexigram.contracts.audit.protocols import AuditLoggerProtocol
from lexigram.contracts.audit.types import AuditQuery


class _FakeRequest:
    def __init__(self, params: dict[str, str] | None = None, path: str = "/admin/audit") -> None:
        self.query_params = params or {}
        self.url = type("Url", (), {"path": path})()


class _FakeLogger:
    def __init__(self, entries: list[AuditEntry] | Exception) -> None:
        self._entries = entries

    async def query(self, q: AuditQuery) -> list[AuditEntry]:
        if isinstance(self._entries, Exception):
            raise self._entries
        return self._entries


def _entry(**kw: Any) -> AuditEntry:
    base = dict(
        action="user.login",
        actor_id="u-1",
        resource_type="User",
        resource_id="u-1",
        outcome="success",
        severity=AuditEventSeverity.MEDIUM,
        occurred_at=datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
        source="admin",
    )
    base.update(kw)
    return AuditEntry(**base)


class TestQueryHelpers:
    def test_query_int_valid(self) -> None:
        assert _query_int(_FakeRequest({"page": "3"}), "page", 1, 1, 10) == 3

    def test_query_int_invalid_falls_back(self) -> None:
        req = _FakeRequest({"page": "abc"})
        assert _query_int(req, "page", 1, 1, 10) == 1
        assert _query_int(req, "missing", 5, 1, 10) == 5

    def test_query_int_clamped(self) -> None:
        req = _FakeRequest({"page": "999"})
        assert _query_int(req, "page", 1, 1, 10) == 10
        assert _query_int(_FakeRequest({"page": "-5"}), "page", 1, 1, 10) == 1

    def test_paging(self) -> None:
        page, per_page = _paging(_FakeRequest({"page": "2", "per_page": "50"}))
        assert (page, per_page) == (2, 50)

    def test_paging_defaults(self) -> None:
        page, per_page = _paging(_FakeRequest())
        assert (page, per_page) == (1, 20)

    def test_paging_clamps_per_page(self) -> None:
        page, per_page = _paging(_FakeRequest({"per_page": "9999"}))
        assert per_page == 200

    def test_pagination_block_empty(self) -> None:
        assert _pagination_block(1, 0, 20, "/admin/audit") == ""

    def test_pagination_block_renders(self) -> None:
        from lexigram.ui import render_to_string

        block = render_to_string(_pagination_block(1, 45, 20, "/admin/audit"))
        assert "Showing" in block
        assert "45" in block


class TestAuditLogPage:
    def test_no_logger_unavailable(self) -> None:
        response = asyncio.run(AuditLogPage(audit_logger=None).handle(_FakeRequest()))
        assert "Audit Log Unavailable" in response.body.decode()

    def test_query_failure_treats_as_empty(self) -> None:
        page = AuditLogPage(audit_logger=_FakeLogger(RuntimeError("boom")))
        response = asyncio.run(page.handle(_FakeRequest()))
        assert "Audit Log" in response.body.decode()

    def test_renders_entries(self) -> None:
        entries = [
            _entry(severity=AuditEventSeverity.HIGH, action="user.delete", resource_id=""),
            _entry(severity=AuditEventSeverity.MEDIUM, outcome="failure"),
        ]
        page = AuditLogPage(audit_logger=_FakeLogger(entries))
        html = asyncio.run(page.handle(_FakeRequest())).body.decode()
        assert "user.delete" in html
        assert "2026-01-02 03:04" in html
        assert "u-1" in html

    def test_high_counter(self) -> None:
        entries = [
            _entry(severity=AuditEventSeverity.HIGH),
            _entry(severity=AuditEventSeverity.CRITICAL),
            _entry(severity=AuditEventSeverity.LOW),
        ]
        page = AuditLogPage(audit_logger=_FakeLogger(entries))
        html = asyncio.run(page.handle(_FakeRequest())).body.decode()
        assert ">2<" in html

    def test_pagination_with_many_entries(self) -> None:
        entries = [_entry(action=f"act.{i}") for i in range(45)]
        page = AuditLogPage(audit_logger=_FakeLogger(entries))
        html = asyncio.run(page.handle(_FakeRequest({"page": "99"}))).body.decode()
        assert "45" in html