"""Tests for AuditQueryService — query, CSV/JSON export, and summary.

Uses InMemoryAuditStore as the backing store so tests are fully
self-contained with no external dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.ai.governance.audit.memory import InMemoryAuditStore
from lexigram.ai.governance.audit.models import AIAuditEvent, AuditEventType, AuditQuery
from lexigram.ai.governance.audit.query import AuditQueryService
from lexigram.serialization import loads_str

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _event(
    model: str = "gpt-4",
    user_id: str = "user-1",
    status: str = "success",
    tokens: int | None = 100,
    cost: float | None = 0.01,
    event_type: AuditEventType = AuditEventType.LLM_CALL,
    ts_offset_seconds: float = 0,
) -> AIAuditEvent:
    return AIAuditEvent(
        event_type=event_type,
        model=model,
        user_id=user_id,
        status=status,
        tokens=tokens,
        cost=cost,
        timestamp=datetime.now(UTC) - timedelta(seconds=ts_offset_seconds),
    )


async def _store_with_events(events: list[AIAuditEvent]) -> InMemoryAuditStore:
    store = InMemoryAuditStore()
    for evt in events:
        await store.record(evt)
    return store


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------


class TestAuditQueryServiceQuery:
    @pytest.mark.asyncio
    async def test_query_returns_all_events_when_no_filter(self) -> None:
        store = await _store_with_events([_event(), _event(), _event()])
        svc = AuditQueryService(store=store)
        events = await svc.query()
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_query_filters_by_model(self) -> None:
        store = await _store_with_events(
            [_event(model="gpt-4"), _event(model="claude-3"), _event(model="gpt-4")]
        )
        svc = AuditQueryService(store=store)
        events = await svc.query(model="gpt-4")
        assert len(events) == 2
        assert all(e.model == "gpt-4" for e in events)

    @pytest.mark.asyncio
    async def test_query_filters_by_tenant_id(self) -> None:
        store = await _store_with_events(
            [
                _event(user_id="tenant-a"),
                _event(user_id="tenant-b"),
                _event(user_id="tenant-a"),
            ]
        )
        svc = AuditQueryService(store=store)
        events = await svc.query(tenant_id="tenant-a")
        assert len(events) == 2
        assert all(e.user_id == "tenant-a" for e in events)

    @pytest.mark.asyncio
    async def test_query_filters_by_time_range(self) -> None:
        now = datetime.now(UTC)
        old_event = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL,
            model="gpt-4",
            timestamp=now - timedelta(hours=2),
        )
        recent_event = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL,
            model="gpt-4",
            timestamp=now - timedelta(minutes=10),
        )
        store = await _store_with_events([old_event, recent_event])
        svc = AuditQueryService(store=store)

        events = await svc.query(start=now - timedelta(hours=1))
        assert len(events) == 1
        assert events[0].event_id == recent_event.event_id

    @pytest.mark.asyncio
    async def test_query_respects_limit(self) -> None:
        store = await _store_with_events([_event() for _ in range(20)])
        svc = AuditQueryService(store=store)
        events = await svc.query(limit=5)
        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_query_returns_empty_for_no_matching_model(self) -> None:
        store = await _store_with_events([_event(model="gpt-4")])
        svc = AuditQueryService(store=store)
        events = await svc.query(model="nonexistent-model")
        assert events == []

    @pytest.mark.asyncio
    async def test_query_combines_model_and_tenant_filters(self) -> None:
        store = await _store_with_events(
            [
                _event(model="gpt-4", user_id="tenant-a"),
                _event(model="gpt-4", user_id="tenant-b"),
                _event(model="claude-3", user_id="tenant-a"),
            ]
        )
        svc = AuditQueryService(store=store)
        events = await svc.query(model="gpt-4", tenant_id="tenant-a")
        assert len(events) == 1
        assert events[0].model == "gpt-4"
        assert events[0].user_id == "tenant-a"


# ---------------------------------------------------------------------------
# export_csv()
# ---------------------------------------------------------------------------


class TestAuditQueryServiceExportCsv:
    @pytest.mark.asyncio
    async def test_export_csv_yields_header_first_chunk(self) -> None:
        store = await _store_with_events([_event()])
        svc = AuditQueryService(store=store)
        chunks: list[bytes] = []
        async for chunk in svc.export_csv(AuditQuery()):
            chunks.append(chunk)

        header = chunks[0].decode()
        assert "event_id" in header
        assert "event_type" in header
        assert "timestamp" in header
        assert "model" in header

    @pytest.mark.asyncio
    async def test_export_csv_contains_event_data(self) -> None:
        evt = _event(model="gpt-4", user_id="user-42", status="success")
        store = await _store_with_events([evt])
        svc = AuditQueryService(store=store)
        all_bytes = b""
        async for chunk in svc.export_csv(AuditQuery()):
            all_bytes += chunk

        csv_text = all_bytes.decode()
        assert "gpt-4" in csv_text
        assert "user-42" in csv_text
        assert "success" in csv_text
        assert evt.event_id in csv_text

    @pytest.mark.asyncio
    async def test_export_csv_empty_store_yields_header_only(self) -> None:
        store = InMemoryAuditStore()
        svc = AuditQueryService(store=store)
        chunks: list[bytes] = []
        async for chunk in svc.export_csv(AuditQuery()):
            chunks.append(chunk)

        # Only the header chunk
        assert len(chunks) == 1
        assert b"event_id" in chunks[0]

    @pytest.mark.asyncio
    async def test_export_csv_multiple_events(self) -> None:
        events = [_event(model=f"model-{i}") for i in range(5)]
        store = await _store_with_events(events)
        svc = AuditQueryService(store=store)
        all_bytes = b""
        async for chunk in svc.export_csv(AuditQuery()):
            all_bytes += chunk

        csv_text = all_bytes.decode()
        for i in range(5):
            assert f"model-{i}" in csv_text

    @pytest.mark.asyncio
    async def test_export_csv_respects_query_model_filter(self) -> None:
        store = await _store_with_events(
            [_event(model="gpt-4"), _event(model="claude-3")]
        )
        svc = AuditQueryService(store=store)
        all_bytes = b""
        async for chunk in svc.export_csv(AuditQuery(model="gpt-4")):
            all_bytes += chunk

        csv_text = all_bytes.decode()
        assert "gpt-4" in csv_text
        assert "claude-3" not in csv_text


# ---------------------------------------------------------------------------
# export_json()
# ---------------------------------------------------------------------------


class TestAuditQueryServiceExportJson:
    @pytest.mark.asyncio
    async def test_export_json_yields_ndjson(self) -> None:
        evt = _event(model="gpt-4", user_id="user-1")
        store = await _store_with_events([evt])
        svc = AuditQueryService(store=store)
        all_bytes = b""
        async for chunk in svc.export_json(AuditQuery()):
            all_bytes += chunk

        lines = [ln for ln in all_bytes.decode().strip().splitlines() if ln]
        assert len(lines) == 1
        record = loads_str(lines[0])
        assert record["model"] == "gpt-4"
        assert record["user_id"] == "user-1"
        assert record["event_id"] == evt.event_id

    @pytest.mark.asyncio
    async def test_export_json_each_line_valid_json(self) -> None:
        events = [_event(model=f"m-{i}") for i in range(10)]
        store = await _store_with_events(events)
        svc = AuditQueryService(store=store)
        all_bytes = b""
        async for chunk in svc.export_json(AuditQuery()):
            all_bytes += chunk

        lines = [ln for ln in all_bytes.decode().strip().splitlines() if ln]
        assert len(lines) == 10
        for line in lines:
            record = loads_str(line)
            assert "event_id" in record
            assert "event_type" in record

    @pytest.mark.asyncio
    async def test_export_json_empty_store_yields_nothing(self) -> None:
        store = InMemoryAuditStore()
        svc = AuditQueryService(store=store)
        chunks: list[bytes] = []
        async for chunk in svc.export_json(AuditQuery()):
            chunks.append(chunk)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_export_json_respects_query_filter(self) -> None:
        store = await _store_with_events(
            [_event(model="gpt-4"), _event(model="claude-3")]
        )
        svc = AuditQueryService(store=store)
        all_bytes = b""
        async for chunk in svc.export_json(AuditQuery(model="claude-3")):
            all_bytes += chunk

        lines = [ln for ln in all_bytes.decode().strip().splitlines() if ln]
        assert len(lines) == 1
        assert loads_str(lines[0])["model"] == "claude-3"


# ---------------------------------------------------------------------------
# summary()
# ---------------------------------------------------------------------------


class TestAuditQueryServiceSummary:
    @pytest.mark.asyncio
    async def test_summary_counts_total_events(self) -> None:
        store = await _store_with_events([_event() for _ in range(5)])
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=1)
        assert summary.total_events == 5

    @pytest.mark.asyncio
    async def test_summary_sums_spend(self) -> None:
        events = [_event(cost=0.05) for _ in range(4)]
        store = await _store_with_events(events)
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=1)
        assert abs(summary.total_spend - 0.20) < 1e-9

    @pytest.mark.asyncio
    async def test_summary_sums_tokens(self) -> None:
        events = [_event(tokens=200) for _ in range(3)]
        store = await _store_with_events(events)
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=1)
        assert summary.total_tokens == 600

    @pytest.mark.asyncio
    async def test_summary_counts_denied_events(self) -> None:
        store = await _store_with_events(
            [
                _event(status="denied"),
                _event(status="denied"),
                _event(status="success"),
            ]
        )
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=1)
        assert summary.denied_count == 2

    @pytest.mark.asyncio
    async def test_summary_by_model_breakdown(self) -> None:
        store = await _store_with_events(
            [
                _event(model="gpt-4"),
                _event(model="gpt-4"),
                _event(model="claude-3"),
            ]
        )
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=1)
        assert summary.by_model["gpt-4"] == 2
        assert summary.by_model["claude-3"] == 1

    @pytest.mark.asyncio
    async def test_summary_by_user_breakdown(self) -> None:
        store = await _store_with_events(
            [
                _event(user_id="alice"),
                _event(user_id="bob"),
                _event(user_id="alice"),
            ]
        )
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=1)
        assert summary.by_user["alice"] == 2
        assert summary.by_user["bob"] == 1

    @pytest.mark.asyncio
    async def test_summary_excludes_events_outside_window(self) -> None:
        old_event = AIAuditEvent(
            event_type=AuditEventType.LLM_CALL,
            model="gpt-4",
            timestamp=datetime.now(UTC) - timedelta(hours=25),
        )
        recent_event = _event()
        store = await _store_with_events([old_event, recent_event])
        svc = AuditQueryService(store=store)
        summary = await svc.summary(window_hours=24)
        assert summary.total_events == 1

    @pytest.mark.asyncio
    async def test_summary_empty_store_returns_zero_counts(self) -> None:
        store = InMemoryAuditStore()
        svc = AuditQueryService(store=store)
        summary = await svc.summary()
        assert summary.total_events == 0
        assert summary.total_spend == 0.0
        assert summary.total_tokens == 0
        assert summary.denied_count == 0
