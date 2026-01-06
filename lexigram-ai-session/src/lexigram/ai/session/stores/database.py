"""SQL-backed session store via the DatabaseProviderProtocol."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from lexigram.contracts.ai.session import (
    SessionCheckpoint,
    SessionState,
    SessionStatus,
    SessionTurn,
)
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization.backends.json import dumps_str, loads

logger = get_logger(__name__)

# SQL DDL (informational — run once via migration tool)
_CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS ai_sessions (
    session_id          TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    status              TEXT NOT NULL,
    turns               TEXT NOT NULL DEFAULT '[]',
    metadata            TEXT NOT NULL DEFAULT '{}',
    active_tools        TEXT NOT NULL DEFAULT '[]',
    active_skills       TEXT NOT NULL DEFAULT '[]',
    system_prompt       TEXT,
    variables           TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    checkpoint_id       TEXT,
    total_tokens        INTEGER NOT NULL DEFAULT 0,
    total_cost          REAL NOT NULL DEFAULT 0.0,
    turn_count          INTEGER NOT NULL DEFAULT 0,
    parent_session_id   TEXT,
    branch_name         TEXT
);
"""

_CREATE_CHECKPOINTS_TABLE = """
CREATE TABLE IF NOT EXISTS ai_checkpoints (
    checkpoint_id       TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL,
    state               TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    metadata            TEXT NOT NULL DEFAULT '{}'
);
"""


def _row_to_state(row: Any) -> SessionState:
    """Convert a DB row (sequence or mapping) to a ``SessionState``."""
    turns_raw = loads(row[3] if isinstance(row, (list, tuple)) else row["turns"])
    turns = [
        SessionTurn(
            turn_id=t["turn_id"],
            role=t["role"],
            content=t["content"],
            timestamp=datetime.fromisoformat(t["timestamp"]),
            tool_calls=t.get("tool_calls", []),
            skill_results=t.get("skill_results", []),
            metadata=t.get("metadata", {}),
            tokens_used=t.get("tokens_used", 0),
            cost=t.get("cost", 0.0),
            model=t.get("model"),
            provider=t.get("provider"),
        )
        for t in turns_raw
    ]

    def _col(row: Any, idx: int, name: str) -> Any:
        if isinstance(row, (list, tuple)):
            return row[idx]
        return row[name]

    return SessionState(
        session_id=_col(row, 0, "session_id"),
        user_id=_col(row, 1, "user_id"),
        status=SessionStatus(_col(row, 2, "status")),
        turns=turns,
        metadata=loads(_col(row, 4, "metadata")),
        active_tools=loads(_col(row, 5, "active_tools")),
        active_skills=loads(_col(row, 6, "active_skills")),
        system_prompt=_col(row, 7, "system_prompt"),
        variables=loads(_col(row, 8, "variables")),
        created_at=datetime.fromisoformat(_col(row, 9, "created_at")),
        updated_at=datetime.fromisoformat(_col(row, 10, "updated_at")),
        checkpoint_id=_col(row, 11, "checkpoint_id"),
        total_tokens=_col(row, 12, "total_tokens"),
        total_cost=_col(row, 13, "total_cost"),
        turn_count=_col(row, 14, "turn_count"),
        parent_session_id=_col(row, 15, "parent_session_id"),
        branch_name=_col(row, 16, "branch_name"),
    )


class DatabaseSessionStore:
    """SQL-backed session store for durable production storage.

    Uses ``DatabaseProviderProtocol`` from ``lexigram-contracts`` so the
    concrete driver (asyncpg, aiosqlite, …) is never imported directly.
    All state is JSON-serialised for the SQL TEXT columns.

    Tables used:
    - ``ai_sessions``   — one row per session
    - ``ai_checkpoints`` — one row per checkpoint

    Args:
        db: Any object implementing ``DatabaseProviderProtocol``
            (provides ``scoped_context()`` and ``get_scoped_connection()``).
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def save(self, state: SessionState) -> None:
        """Upsert *state* in the database.

        Args:
            state: The session state to persist.
        """
        turns_json = dumps_str(
            [
                {
                    "turn_id": t.turn_id,
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat(),
                    "tool_calls": t.tool_calls,
                    "skill_results": t.skill_results,
                    "metadata": t.metadata,
                    "tokens_used": t.tokens_used,
                    "cost": t.cost,
                    "model": t.model,
                    "provider": t.provider,
                }
                for t in state.turns
            ]
        )
        sql = """
            INSERT INTO ai_sessions
                (session_id, user_id, status, turns, metadata, active_tools,
                 active_skills, system_prompt, variables, created_at, updated_at,
                 checkpoint_id, total_tokens, total_cost, turn_count,
                 parent_session_id, branch_name)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
            ON CONFLICT (session_id) DO UPDATE SET
                status=EXCLUDED.status, turns=EXCLUDED.turns,
                metadata=EXCLUDED.metadata, active_tools=EXCLUDED.active_tools,
                active_skills=EXCLUDED.active_skills,
                system_prompt=EXCLUDED.system_prompt,
                variables=EXCLUDED.variables,
                updated_at=EXCLUDED.updated_at,
                checkpoint_id=EXCLUDED.checkpoint_id,
                total_tokens=EXCLUDED.total_tokens,
                total_cost=EXCLUDED.total_cost,
                turn_count=EXCLUDED.turn_count
        """
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(
                sql,
                state.session_id,
                state.user_id,
                state.status.value,
                turns_json,
                dumps_str(state.metadata),
                dumps_str(state.active_tools),
                dumps_str(state.active_skills),
                state.system_prompt,
                dumps_str(state.variables),
                state.created_at.isoformat(),
                state.updated_at.isoformat(),
                state.checkpoint_id,
                state.total_tokens,
                state.total_cost,
                state.turn_count,
                state.parent_session_id,
                state.branch_name,
            )

    async def load(self, session_id: str) -> SessionState | None:
        """Return the session state for *session_id*, or ``None``.

        Args:
            session_id: The session to load.

        Returns:
            Deserialised ``SessionState`` or ``None``.
        """
        sql = "SELECT * FROM ai_sessions WHERE session_id = $1"
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            row = await conn.fetchrow(sql, session_id)
        if row is None:
            return None
        return _row_to_state(row)

    async def delete(self, session_id: str) -> None:
        """Remove a session from the database.

        Args:
            session_id: The session to delete.
        """
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(
                "DELETE FROM ai_sessions WHERE session_id = $1", session_id
            )

    async def list_sessions(self, user_id: str) -> list[SessionState]:
        """List all sessions belonging to *user_id*.

        Args:
            user_id: User to filter by.

        Returns:
            All sessions for that user.
        """
        sql = "SELECT * FROM ai_sessions WHERE user_id = $1 ORDER BY created_at"
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            rows = await conn.fetch(sql, user_id)
        return [_row_to_state(r) for r in rows]

    # ------------------------------------------------------------------
    # Checkpoint CRUD
    # ------------------------------------------------------------------

    async def save_checkpoint(self, checkpoint: SessionCheckpoint) -> None:
        """Persist an immutable checkpoint.

        Args:
            checkpoint: The checkpoint to save.
        """
        from lexigram.ai.session.stores.cache import _state_to_dict  # local helper

        sql = """
            INSERT INTO ai_checkpoints
                (checkpoint_id, session_id, state, created_at,
                 parent_checkpoint_id, metadata)
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (checkpoint_id) DO NOTHING
        """
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(
                sql,
                checkpoint.checkpoint_id,
                checkpoint.session_id,
                dumps_str(_state_to_dict(checkpoint.state)),
                checkpoint.created_at.isoformat(),
                checkpoint.parent_checkpoint_id,
                dumps_str(checkpoint.metadata),
            )

    async def load_checkpoint(self, checkpoint_id: str) -> SessionCheckpoint | None:
        """Return the checkpoint for *checkpoint_id*, or ``None``.

        Args:
            checkpoint_id: The checkpoint to load.

        Returns:
            Deserialised ``SessionCheckpoint`` or ``None``.
        """
        sql = "SELECT * FROM ai_checkpoints WHERE checkpoint_id = $1"
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            row = await conn.fetchrow(sql, checkpoint_id)
        if row is None:
            return None
        return self._row_to_checkpoint(row)

    async def list_checkpoints(self, session_id: str) -> list[SessionCheckpoint]:
        """List all checkpoints for *session_id*, oldest-first.

        Args:
            session_id: The session to query.

        Returns:
            Checkpoints in chronological order.
        """
        sql = "SELECT * FROM ai_checkpoints WHERE session_id = $1 ORDER BY created_at"
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            rows = await conn.fetch(sql, session_id)
        return [self._row_to_checkpoint(r) for r in rows]

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Remove a checkpoint from the database.

        Args:
            checkpoint_id: The checkpoint to delete.
        """
        async with self._db.scoped_context():
            conn = await self._db.get_scoped_connection()
            await conn.execute(
                "DELETE FROM ai_checkpoints WHERE checkpoint_id = $1", checkpoint_id
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_checkpoint(row: Any) -> SessionCheckpoint:
        """Deserialise a DB row to a ``SessionCheckpoint``."""
        from lexigram.ai.session.stores.cache import _dict_to_state  # local helper

        def _col(row: Any, idx: int, name: str) -> Any:
            if isinstance(row, (list, tuple)):
                return row[idx]
            return row[name]

        state_dict = loads(_col(row, 2, "state"))
        return SessionCheckpoint(
            checkpoint_id=_col(row, 0, "checkpoint_id"),
            session_id=_col(row, 1, "session_id"),
            state=_dict_to_state(state_dict),
            created_at=datetime.fromisoformat(_col(row, 3, "created_at")),
            parent_checkpoint_id=_col(row, 4, "parent_checkpoint_id"),
            metadata=loads(_col(row, 5, "metadata")),
        )


__all__ = ["DatabaseSessionStore"]
