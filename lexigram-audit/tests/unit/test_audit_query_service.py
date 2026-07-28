"""Tests for AuditQueryService (LXF-003)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.audit.query import AuditQueryService
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditQuery


class TestAuditQueryService:
    """Tests for AuditQueryService convenience methods."""

    @pytest.fixture
    def service(self) -> AuditQueryService:
        return AuditQueryService(InMemoryAuditStore())

    @pytest.fixture
    async def populated_service(self, service: AuditQueryService) -> AuditQueryService:
        now = datetime.now(UTC)
        for i in range(3):
            await service._store.append(AuditEntry(
                action="llm.completion",
                actor_id="svc-1",
                outcome="success",
                tenant_id=f"tenant-{i}",
                correlation_id=f"corr-{i}",
            ))
        return service

    @pytest.mark.asyncio
    async def test_query_by_tenant_returns_matching(self, populated_service: AuditQueryService) -> None:
        service = populated_service
        since = datetime.now(UTC) - timedelta(hours=1)
        until = datetime.now(UTC) + timedelta(hours=1)
        results = await service.query_by_tenant("tenant-0", since=since, until=until)
        assert len(results) == 1
        assert results[0].tenant_id == "tenant-0"

    @pytest.mark.asyncio
    async def test_query_by_tenant_filters_action(self, populated_service: AuditQueryService) -> None:
        service = populated_service
        now = datetime.now(UTC)
        results = await service.query_by_tenant(
            "tenant-0", since=now - timedelta(hours=1), until=now + timedelta(hours=1),
            actions=["llm.completion"],
        )
        assert len(results) == 1
        assert results[0].action == "llm.completion"

    @pytest.mark.asyncio
    async def test_query_by_tenant_respects_limit(self, populated_service: AuditQueryService) -> None:
        service = populated_service
        now = datetime.now(UTC)
        results = await service.query_by_tenant(
            "tenant-1", since=now - timedelta(hours=1), until=now + timedelta(hours=1),
            limit=1,
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_by_tenant_no_match(self, populated_service: AuditQueryService) -> None:
        service = populated_service
        now = datetime.now(UTC)
        results = await service.query_by_tenant(
            "nonexistent", since=now - timedelta(hours=1), until=now + timedelta(hours=1),
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_by_correlation_returns_matching(self, populated_service: AuditQueryService) -> None:
        service = populated_service
        results = await service.query_by_correlation("corr-2")
        assert len(results) == 1
        assert results[0].correlation_id == "corr-2"

    @pytest.mark.asyncio
    async def test_query_by_correlation_no_match(self, populated_service: AuditQueryService) -> None:
        service = populated_service
        results = await service.query_by_correlation("nonexistent")
        assert len(results) == 0
