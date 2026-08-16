"""Unit tests for state transition persistence implementations."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from lexigram.contracts.data import DatabaseProviderProtocol, QueryResult
from lexigram.workflow.state.persistence import DatabaseStatePersistence


class _NoopTransaction:
    """Minimal async context manager used for provider.transaction()."""

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _query_result(rows: list[dict[str, object]]) -> QueryResult:
    return QueryResult(
        rows=rows,
        row_count=len(rows),
        execution_time=0.0,
        success=True,
    )


@pytest.mark.asyncio
async def test_append_transition_persists_and_returns_next_version() -> None:
    provider = MagicMock(spec=DatabaseProviderProtocol)
    provider.transaction = MagicMock(return_value=_NoopTransaction())
    provider.execute = AsyncMock(return_value=_query_result([]))
    provider.execute_query = AsyncMock(return_value=_query_result([{"version": 0}]))
    provider.execute_insert = AsyncMock()

    persistence = DatabaseStatePersistence(provider)

    next_version = await persistence.append_transition(
        machine_id="order-1",
        from_state="idle",
        event="start",
        to_state="running",
        expected_version=0,
    )

    assert next_version == 1
    provider.execute.assert_awaited_once()
    provider.execute_insert.assert_awaited_once_with(
        "workflow_state_transitions",
        {
            "machine_id": "order-1",
            "version": 1,
            "from_state": "idle",
            "event": "start",
            "to_state": "running",
            "transitioned_at": ANY,
        },
    )


@pytest.mark.asyncio
async def test_append_transition_raises_on_optimistic_lock_conflict() -> None:
    provider = MagicMock(spec=DatabaseProviderProtocol)
    provider.transaction = MagicMock(return_value=_NoopTransaction())
    provider.execute = AsyncMock(return_value=_query_result([]))
    provider.execute_query = AsyncMock(return_value=_query_result([{"version": 2}]))
    provider.execute_insert = AsyncMock()

    persistence = DatabaseStatePersistence(provider)

    with pytest.raises(RuntimeError, match="Optimistic lock failed"):
        await persistence.append_transition(
            machine_id="order-1",
            from_state="idle",
            event="start",
            to_state="running",
            expected_version=1,
        )

    provider.execute_insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_transitions_maps_rows_to_records() -> None:
    provider = MagicMock(spec=DatabaseProviderProtocol)
    provider.transaction = MagicMock(return_value=_NoopTransaction())
    provider.execute = AsyncMock(return_value=_query_result([]))
    provider.execute_query = AsyncMock(
        return_value=_query_result(
            [
                {
                    "machine_id": "order-1",
                    "version": 1,
                    "from_state": "idle",
                    "event": "start",
                    "to_state": "running",
                    "transitioned_at": 100.0,
                },
                {
                    "machine_id": "order-1",
                    "version": 2,
                    "from_state": "running",
                    "event": "complete",
                    "to_state": "done",
                    "transitioned_at": 200.0,
                },
            ]
        )
    )
    provider.execute_insert = AsyncMock()

    persistence = DatabaseStatePersistence(provider)

    records = await persistence.load_transitions("order-1")

    assert len(records) == 2
    assert records[0].from_state == "idle"
    assert records[0].to_state == "running"
    assert records[1].from_state == "running"
    assert records[1].to_state == "done"


def test_invalid_table_name_is_rejected() -> None:
    provider = MagicMock(spec=DatabaseProviderProtocol)

    with pytest.raises(ValueError, match="Invalid table name"):
        DatabaseStatePersistence(provider, table_name="workflow-transitions")
