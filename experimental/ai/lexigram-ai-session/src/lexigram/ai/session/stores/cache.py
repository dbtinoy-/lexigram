"""Redis-backed session store via the CacheBackendProtocol protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from lexigram.contracts.ai.session import (
    SessionCheckpoint,
    SessionState,
    SessionStatus,
    SessionTurn,
)
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.logging import (
    get_logger,
)
from lexigram.serialization.backends.json import dumps_str, loads

logger = get_logger(__name__)

_SESSION_PREFIX = "ai:session:"
_CHECKPOINT_PREFIX = "ai:checkpoint:"
_USER_INDEX_PREFIX = "ai:session:user:"


def _state_to_dict(state: SessionState) -> dict[str, Any]:
    """Serialise a ``SessionState`` to a JSON-compatible dict."""
    return {
        "session_id": state.session_id,
        "user_id": state.user_id,
        "status": state.status.value,
        "turns": [
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
        ],
        "metadata": state.metadata,
        "active_tools": state.active_tools,
        "active_skills": state.active_skills,
        "system_prompt": state.system_prompt,
        "variables": state.variables,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "checkpoint_id": state.checkpoint_id,
        "total_tokens": state.total_tokens,
        "total_cost": state.total_cost,
        "turn_count": state.turn_count,
        "parent_session_id": state.parent_session_id,
        "branch_name": state.branch_name,
    }


def _dict_to_state(d: dict[str, Any]) -> SessionState:
    """Deserialise a dict back to a ``SessionState``."""
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
        for t in d.get("turns", [])
    ]
    return SessionState(
        session_id=d["session_id"],
        user_id=d["user_id"],
        status=SessionStatus(d["status"]),
        turns=turns,
        metadata=d.get("metadata", {}),
        active_tools=d.get("active_tools", []),
        active_skills=d.get("active_skills", []),
        system_prompt=d.get("system_prompt"),
        variables=d.get("variables", {}),
        created_at=datetime.fromisoformat(d["created_at"]),
        updated_at=datetime.fromisoformat(d["updated_at"]),
        checkpoint_id=d.get("checkpoint_id"),
        total_tokens=d.get("total_tokens", 0),
        total_cost=d.get("total_cost", 0.0),
        turn_count=d.get("turn_count", 0),
        parent_session_id=d.get("parent_session_id"),
        branch_name=d.get("branch_name"),
    )


def _checkpoint_to_dict(cp: SessionCheckpoint) -> dict[str, Any]:
    """Serialise a ``SessionCheckpoint`` to a JSON-compatible dict."""
    return {
        "checkpoint_id": cp.checkpoint_id,
        "session_id": cp.session_id,
        "state": _state_to_dict(cp.state),
        "created_at": cp.created_at.isoformat(),
        "parent_checkpoint_id": cp.parent_checkpoint_id,
        "metadata": cp.metadata,
    }


def _dict_to_checkpoint(d: dict[str, Any]) -> SessionCheckpoint:
    """Deserialise a dict back to a ``SessionCheckpoint``."""
    return SessionCheckpoint(
        checkpoint_id=d["checkpoint_id"],
        session_id=d["session_id"],
        state=_dict_to_state(d["state"]),
        created_at=datetime.fromisoformat(d["created_at"]),
        parent_checkpoint_id=d.get("parent_checkpoint_id"),
        metadata=d.get("metadata", {}),
    )


class CacheSessionStore:
    """Redis-backed session store for multi-process deployments.

    Uses the ``CacheBackendProtocol`` protocol from ``lexigram-contracts`` so the
    concrete Redis client is never imported directly.  Sessions and
    checkpoints are JSON-serialised.  A per-user set index tracks which
    sessions belong to a given user.

    Args:
        cache: Any object implementing ``CacheBackendProtocol`` (get/set/delete).
        ttl: Session TTL in seconds (default 24 h).
    """

    def __init__(self, cache: CacheBackendProtocol, ttl: int = 86400) -> None:
        self._cache = cache
        self._ttl = ttl

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    async def save(self, state: SessionState) -> None:
        """Persist *state* in the cache.

        Args:
            state: Session state to save.
        """
        key = _SESSION_PREFIX + state.session_id
        payload = dumps_str(_state_to_dict(state))
        await self._cache.set(key, payload, ttl=self._ttl)
        # Maintain user → session_id index
        index_key = _USER_INDEX_PREFIX + state.user_id
        existing_raw = await self._cache.get(index_key)
        ids: list[str] = loads(existing_raw) if existing_raw else []  # type: ignore[arg-type]
        if state.session_id not in ids:
            ids.append(state.session_id)
        await self._cache.set(index_key, dumps_str(ids), ttl=self._ttl)

    async def load(self, session_id: str) -> SessionState | None:
        """Return the session state for *session_id*, or ``None``.

        Args:
            session_id: The session to load.

        Returns:
            Deserialised ``SessionState`` or ``None``.
        """
        raw = await self._cache.get(_SESSION_PREFIX + session_id)
        if raw is None:
            return None
        return _dict_to_state(loads(raw))  # type: ignore[arg-type]

    async def delete(self, session_id: str) -> None:
        """Remove a session from the cache.

        Args:
            session_id: The session to delete.
        """
        await self._cache.delete(_SESSION_PREFIX + session_id)

    async def list_sessions(self, user_id: str) -> list[SessionState]:
        """List all sessions for *user_id*.

        Args:
            user_id: The user to query.

        Returns:
            All sessions found for that user.
        """
        index_key = _USER_INDEX_PREFIX + user_id
        raw = await self._cache.get(index_key)
        if not raw:
            return []
        ids = loads(raw)  # type: ignore[arg-type]
        results: list[SessionState] = []
        for sid in ids:
            state = await self.load(sid)
            if state is not None:
                results.append(state)
        return results

    # ------------------------------------------------------------------
    # Checkpoint CRUD
    # ------------------------------------------------------------------

    async def save_checkpoint(self, checkpoint: SessionCheckpoint) -> None:
        """Persist a checkpoint in the cache.

        Args:
            checkpoint: The checkpoint to save.
        """
        key = _CHECKPOINT_PREFIX + checkpoint.checkpoint_id
        payload = dumps_str(_checkpoint_to_dict(checkpoint))
        await self._cache.set(key, payload, ttl=self._ttl)
        # Maintain session → checkpoint_id index
        idx_key = _CHECKPOINT_PREFIX + "idx:" + checkpoint.session_id
        raw = await self._cache.get(idx_key)
        ids: list[str] = loads(raw) if raw else []  # type: ignore[arg-type]
        if checkpoint.checkpoint_id not in ids:
            ids.append(checkpoint.checkpoint_id)
        await self._cache.set(idx_key, dumps_str(ids), ttl=self._ttl)

    async def load_checkpoint(self, checkpoint_id: str) -> SessionCheckpoint | None:
        """Return the checkpoint for *checkpoint_id*, or ``None``.

        Args:
            checkpoint_id: The checkpoint to load.

        Returns:
            Deserialised ``SessionCheckpoint`` or ``None``.
        """
        raw = await self._cache.get(_CHECKPOINT_PREFIX + checkpoint_id)
        if raw is None:
            return None
        return _dict_to_checkpoint(loads(raw))  # type: ignore[arg-type]

    async def list_checkpoints(self, session_id: str) -> list[SessionCheckpoint]:
        """List all checkpoints for *session_id*, oldest-first.

        Args:
            session_id: The session to query.

        Returns:
            Checkpoints in chronological order.
        """
        idx_key = _CHECKPOINT_PREFIX + "idx:" + session_id
        raw = await self._cache.get(idx_key)
        if not raw:
            return []
        ids: list[str] = loads(raw)  # type: ignore[arg-type]
        checkpoints: list[SessionCheckpoint] = []
        for cid in ids:
            cp = await self.load_checkpoint(cid)
            if cp is not None:
                checkpoints.append(cp)
        return sorted(checkpoints, key=lambda c: c.created_at)

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Remove a checkpoint from the cache.

        Args:
            checkpoint_id: The checkpoint to delete.
        """
        await self._cache.delete(_CHECKPOINT_PREFIX + checkpoint_id)


__all__ = ["CacheSessionStore"]
