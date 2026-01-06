"""Tests for AuditAdminContributor."""

from __future__ import annotations

import json

import pytest

from lexigram.audit.admin.contributor import AuditAdminContributor
from lexigram.audit.logging.logger import AuditLogger
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditQuery


class TestAuditAdminContributor:
    """Tests for AuditAdminContributor."""

    @pytest.fixture
    def contributor(self) -> AuditAdminContributor:
        store = InMemoryAuditStore()
        audit_logger = AuditLogger(store=store)
        c = AuditAdminContributor()
        c._logger = audit_logger  # inject directly for unit tests
        return c

    @pytest.mark.asyncio
    async def test_get_nav_items(self, contributor: AuditAdminContributor) -> None:
        items = contributor.get_navigation_items()
        assert len(items) == 1
        assert items[0].label == "Audit"
        assert items[0].icon == "shield-check"
        assert len(items[0].children) == 2

        pages = contributor.get_management_pages()
        assert len(pages) == 2
        assert pages[0].name == "audit_log"
        assert pages[1].name == "audit_verification"

    @pytest.mark.asyncio
    async def test_search_delegates_to_logger(self, contributor: AuditAdminContributor) -> None:
        await contributor._logger.log(
            AuditEntry(action="user.login", actor_id="u-1", outcome="success")
        )
        results = await contributor.search(AuditQuery(actor_id="u-1"))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_export_json(self, contributor: AuditAdminContributor) -> None:
        await contributor._logger.log(
            AuditEntry(action="user.login", actor_id="u-1", outcome="success")
        )
        data = await contributor.export(AuditQuery(), format="json")
        assert isinstance(data, bytes)
        parsed = json.loads(data)
        assert len(parsed) == 1
        assert parsed[0]["action"] == "user.login"

    @pytest.mark.asyncio
    async def test_export_csv(self, contributor: AuditAdminContributor) -> None:
        await contributor._logger.log(
            AuditEntry(action="user.login", actor_id="u-1", outcome="success")
        )
        data = await contributor.export(AuditQuery(), format="csv")
        assert b"user.login" in data

    @pytest.mark.asyncio
    async def test_verification_status_no_verifier(self, contributor: AuditAdminContributor) -> None:
        status = await contributor.verification_status()
        assert status["verified"] is None
