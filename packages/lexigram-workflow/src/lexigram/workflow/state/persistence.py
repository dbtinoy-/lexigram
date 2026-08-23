"""State transition persistence implementations for workflow state machines."""

from __future__ import annotations

import asyncio
import re
import time
from typing import TYPE_CHECKING

from lexigram.contracts.workflow import (
    StatePersistenceProtocol,
    StateTransitionRecord,
)
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseStatePersistence(StatePersistenceProtocol):
    """Database-backed append-only state transition persistence.

    Persists every transition as a row in a transition log table and enforces
    optimistic locking via a monotonic ``version`` column scoped per machine.

    Args:
        provider: Database provider protocol implementation.
        table_name: SQL table used for transition log records.
    """

    def __init__(
        self,
        provider: DatabaseProviderProtocol,
        table_name: str = "workflow_state_transitions",
    ) -> None:
        if not _TABLE_NAME_RE.match(table_name):
            raise ValueError(f"Invalid table name: {table_name!r}")
        self._provider = provider
        self._table_name = table_name
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    async def append_transition(
        self,
        machine_id: str,
        from_state: str,
        event: str,
        to_state: str,
        expected_version: int,
    ) -> int:
        """Persist a transition and return the new version.

        Raises:
            RuntimeError: If persisted version differs from *expected_version*.
        """
        await self._ensure_schema()

        async with self._provider.transaction():
            current_version = await self.get_current_version(machine_id)
            if current_version != expected_version:
                raise RuntimeError(
                    "Optimistic lock failed: "
                    f"expected={expected_version}, actual={current_version}"
                )

            next_version = current_version + 1
            now_ts = time.time()
            await self._provider.execute_insert(
                self._table_name,
                {
                    "machine_id": machine_id,
                    "version": next_version,
                    "from_state": from_state,
                    "event": event,
                    "to_state": to_state,
                    "transitioned_at": now_ts,
                },
            )

            logger.debug(
                "state_persistence.transition_appended",
                machine_id=machine_id,
                from_state=from_state,
                transition_event=event,
                to_state=to_state,
                version=next_version,
            )
            return next_version

    async def load_transitions(self, machine_id: str) -> list[StateTransitionRecord]:
        """Load transitions ordered by version."""
        await self._ensure_schema()
        result = await self._provider.execute_query(
            f"SELECT machine_id, version, from_state, event, to_state, transitioned_at "  # noqa: S608 -- table name allowlisted by _TABLE_NAME_RE in __init__
            f"FROM {self._table_name} "
            "WHERE machine_id = ? "
            "ORDER BY version ASC",
            [machine_id],
        )

        records: list[StateTransitionRecord] = []
        for row in result.rows:
            records.append(
                StateTransitionRecord(
                    machine_id=str(row["machine_id"]),
                    version=int(row["version"]),
                    from_state=str(row["from_state"]),
                    event=str(row["event"]),
                    to_state=str(row["to_state"]),
                    transitioned_at=float(row.get("transitioned_at", 0.0)),
                )
            )
        return records

    async def get_current_version(self, machine_id: str) -> int:
        """Return latest version for machine, or ``0`` when absent."""
        await self._ensure_schema()
        result = await self._provider.execute_query(
            f"SELECT COALESCE(MAX(version), 0) AS version "  # noqa: S608 -- table name allowlisted by _TABLE_NAME_RE in __init__
            f"FROM {self._table_name} "
            "WHERE machine_id = ?",
            [machine_id],
        )
        if not result.rows:
            return 0
        return int(result.rows[0].get("version", 0) or 0)

    async def _ensure_schema(self) -> None:
        """Create persistence table when it does not exist."""
        if self._schema_ready:
            return
        async with self._schema_lock:
            # Re-check under the lock: another coroutine may have completed
            # the DDL between the first check and the lock acquisition.
            if self._schema_ready:
                return  # type: ignore[unreachable]
            await self._provider.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table_name} ("
                "machine_id TEXT NOT NULL,"
                "version INTEGER NOT NULL,"
                "from_state TEXT NOT NULL,"
                "event TEXT NOT NULL,"
                "to_state TEXT NOT NULL,"
                "transitioned_at DOUBLE PRECISION NOT NULL,"
                "PRIMARY KEY(machine_id, version)"
                ")"
            )
            self._schema_ready = True


__all__ = ["DatabaseStatePersistence"]
