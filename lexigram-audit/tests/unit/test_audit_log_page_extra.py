"""Focused tests for the audit log admin page and helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from lexigram.audit.admin.pages.audit_log import (
    AuditLogPage,
    _paging,
    _query_int,
)
from lexigram.contracts.admin import PageContent, PaginationContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity
from lexigram.contracts.audit.types import AuditQuery


class _FakeUrl:
    """Minimal URL stand-in exposing ``path`` and a string form."""

    def __init__(self, path: str = "/admin/audit") -> None:
        self.path = path

    def __str__(self) -> str:
        return f"http://testserver{self.path}"


class _FakeRequest:
    def __init__(
        self, params: dict[str, str] | None = None, path: str = "/admin/audit"
    ) -> None:
        self.query_params = params or {}
        self.url = _FakeUrl(path)


class _FakeLogger:
    def __init__(self, entries: list[AuditEntry] | Exception) -> None:
        self._entries = entries

    async def query(self, q: AuditQuery) -> list[AuditEntry]:
        if isinstance(self._entries, Exception):
            raise self._entries
        return self._entries


def _entry(**kw: Any) -> AuditEntry:
    base = {
        "action": "user.login",
        "actor_id": "u-1",
        "resource_type": "User",
        "resource_id": "u-1",
        "outcome": "success",
        "severity": AuditEventSeverity.MEDIUM,
        "occurred_at": datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
        "source": "admin",
    }
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


class TestAuditLogPage:
    def test_no_logger_unavailable(self) -> None:
        content = asyncio.run(AuditLogPage(audit_logger=None).handle(_FakeRequest()))
        assert isinstance(content, PageContent)
        assert content.title == "Audit Log"
        assert isinstance(content.body, EmptyContent)
        assert content.body.title == "Audit Log Unavailable"
        assert content.body.message == "The audit logger could not be resolved."
        assert content.body.icon == "shield"

    def test_query_failure_treats_as_empty(self) -> None:
        page = AuditLogPage(audit_logger=_FakeLogger(RuntimeError("boom")))
        content = asyncio.run(page.handle(_FakeRequest()))
        assert isinstance(content.body, EmptyContent)
        assert content.body.title == "No Audit Entries"

    def test_renders_entries(self) -> None:
        entries = [
            _entry(
                severity=AuditEventSeverity.HIGH, action="user.delete", resource_id=""
            ),
            _entry(severity=AuditEventSeverity.MEDIUM, outcome="failure"),
        ]
        page = AuditLogPage(audit_logger=_FakeLogger(entries))
        content = asyncio.run(page.handle(_FakeRequest()))
        assert isinstance(content.body, TableContent)
        assert content.body.columns == (
            "Action",
            "Actor",
            "Resource",
            "Outcome",
            "Severity",
            "Timestamp",
            "Source",
        )
        assert len(content.body.rows) == 2
        first = content.body.rows[0]
        assert isinstance(first[0], TableCell)
        assert first[0].text == "user.delete"
        assert first[1].text == "u-1"
        assert first[2].text == "User"
        assert first[3].text == "success"
        assert first[4].text == "high"
        assert first[5].text == "2026-01-02 03:04"
        assert first[6].text == "admin"
        second = content.body.rows[1]
        assert second[2].text == "User/u-1"
        assert second[3].text == "failure"
        assert second[4].text == "medium"

    def test_severity_values_in_rows(self) -> None:
        entries = [
            _entry(severity=AuditEventSeverity.HIGH),
            _entry(severity=AuditEventSeverity.CRITICAL),
            _entry(severity=AuditEventSeverity.LOW),
        ]
        page = AuditLogPage(audit_logger=_FakeLogger(entries))
        content = asyncio.run(page.handle(_FakeRequest()))
        assert isinstance(content.body, TableContent)
        assert [row[4].text for row in content.body.rows] == ["high", "critical", "low"]

    def test_pagination_with_many_entries(self) -> None:
        entries = [_entry(action=f"act.{i}") for i in range(45)]
        page = AuditLogPage(audit_logger=_FakeLogger(entries))
        content = asyncio.run(page.handle(_FakeRequest({"page": "99"})))
        assert isinstance(content.pagination, PaginationContent)
        assert content.pagination.page == 3
        assert content.pagination.total == 45
        assert content.pagination.per_page == 20
        assert content.pagination.base_url == "http://testserver/admin/audit"
        assert isinstance(content.body, TableContent)
        assert len(content.body.rows) == 5
        assert content.body.rows[0][0].text == "act.40"
