"""Unit tests for AdminSessionManager.

Covers:
- Max 5 concurrent sessions with eviction of the oldest.
- Device fingerprinting (unique fingerprints → different device IDs).
- Auto-expiry: expired sessions are revoked and None is returned from validate.
- Full create/validate/revoke lifecycle.
- revoke_all removes all sessions for a user.
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from lexigram.admin.auth.session_manager import AdminSessionManager
from lexigram.contracts.auth.models import UserSession


# ---------------------------------------------------------------------------
# Fake SessionRepositoryProtocol
# ---------------------------------------------------------------------------

class FakeSessionRepository:
    """In-memory SessionRepositoryProtocol for testing."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    async def insert(self, payload: dict[str, Any]) -> None:
        now = datetime.now(UTC)
        row = dict(payload)
        row.setdefault("is_active", True)
        row.setdefault("created_at", now)
        row.setdefault("last_active_at", now)
        self._sessions[payload["session_id"]] = row

    async def find_active(self, session_id: str) -> dict[str, Any] | None:
        row = self._sessions.get(session_id)
        if row is None or not row.get("is_active", True):
            return None
        return dict(row)

    async def find_active_by_user(
        self, user_id: str, cutoff: datetime
    ) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._sessions.values()
            if r.get("admin_id") == user_id
            and r.get("is_active", True)
            and (r.get("expires_at") is None or r["expires_at"] > cutoff)
        ]

    async def revoke(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["is_active"] = False

    async def revoke_all(self, user_id: str) -> None:
        for row in self._sessions.values():
            if row.get("admin_id") == user_id:
                row["is_active"] = False

    async def update_activity(
        self, session_id: str, timestamp: datetime
    ) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["last_active_at"] = timestamp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FINGERPRINT_A = {"browser": "Chrome", "os": "Linux", "screen": "1920x1080"}
_FINGERPRINT_B = {"browser": "Firefox", "os": "macOS", "screen": "2560x1440"}


def _make_manager() -> tuple[AdminSessionManager, FakeSessionRepository]:
    repo = FakeSessionRepository()
    manager = AdminSessionManager(repo)
    return manager, repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_create_returns_user_session(self) -> None:
        manager, _ = _make_manager()
        session = await manager.create_session(
            user_id="user-1",
            fingerprint_data=_FINGERPRINT_A,
        )
        assert isinstance(session, UserSession)
        assert session.user_id == "user-1"
        assert session.is_active is True

    @pytest.mark.asyncio
    async def test_created_session_has_expiry(self) -> None:
        manager, _ = _make_manager()
        now = datetime.now(UTC)
        session = await manager.create_session(
            user_id="user-1",
            fingerprint_data=_FINGERPRINT_A,
            expires_days=7,
        )
        assert session.expires_at is not None
        assert session.expires_at > now + timedelta(days=6)

    @pytest.mark.asyncio
    async def test_device_fingerprints_are_stable(self) -> None:
        """Same fingerprint data → same device_id across two calls."""
        manager, _ = _make_manager()
        s1 = await manager.create_session("u1", _FINGERPRINT_A)
        s2 = await manager.create_session("u1", _FINGERPRINT_A)
        assert s1.device_id == s2.device_id

    @pytest.mark.asyncio
    async def test_different_fingerprints_yield_different_device_ids(self) -> None:
        manager, _ = _make_manager()
        s1 = await manager.create_session("u1", _FINGERPRINT_A)
        s2 = await manager.create_session("u1", _FINGERPRINT_B)
        assert s1.device_id != s2.device_id


class TestMaxConcurrentSessions:
    @pytest.mark.asyncio
    async def test_sixth_session_evicts_oldest(self) -> None:
        """Creating a 6th session must evict the oldest one."""
        manager, repo = _make_manager()

        sessions = []
        for i in range(AdminSessionManager.MAX_CONCURRENT_SESSIONS):
            s = await manager.create_session(
                user_id="user-1",
                fingerprint_data={"index": str(i)},
            )
            sessions.append(s)

        assert len(sessions) == AdminSessionManager.MAX_CONCURRENT_SESSIONS

        # Create the 6th — should evict the oldest (sessions[0])
        new_session = await manager.create_session(
            user_id="user-1",
            fingerprint_data={"index": "new"},
        )

        # Oldest session must now be inactive in the repo
        oldest_row = repo._sessions.get(sessions[0].session_id)
        assert oldest_row is not None
        assert oldest_row["is_active"] is False

        # New session is present and active
        active = await manager.get_active_sessions("user-1")
        active_ids = {s.session_id for s in active}
        assert new_session.session_id in active_ids
        assert sessions[0].session_id not in active_ids

    @pytest.mark.asyncio
    async def test_exactly_max_sessions_allowed_without_eviction(self) -> None:
        manager, repo = _make_manager()
        for i in range(AdminSessionManager.MAX_CONCURRENT_SESSIONS):
            await manager.create_session("user-2", {"n": str(i)})

        active = await manager.get_active_sessions("user-2")
        assert len(active) == AdminSessionManager.MAX_CONCURRENT_SESSIONS

        # All repo rows still active
        for row in repo._sessions.values():
            if row["admin_id"] == "user-2":
                assert row.get("is_active", True) is True


class TestValidateSession:
    @pytest.mark.asyncio
    async def test_validate_active_session_returns_user_session(self) -> None:
        manager, _ = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        result = await manager.validate_session(created.session_id)
        assert result is not None
        assert result.session_id == created.session_id

    @pytest.mark.asyncio
    async def test_validate_missing_session_returns_none(self) -> None:
        manager, _ = _make_manager()
        result = await manager.validate_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_expired_session_returns_none_and_revokes(self) -> None:
        manager, repo = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        session_id = created.session_id

        # Manually set expires_at to the past
        repo._sessions[session_id]["expires_at"] = datetime.now(UTC) - timedelta(hours=1)

        result = await manager.validate_session(session_id)
        assert result is None

        # Session must be revoked in the repo
        assert repo._sessions[session_id]["is_active"] is False

    @pytest.mark.asyncio
    async def test_validate_updates_last_active(self) -> None:
        manager, repo = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        before = datetime.now(UTC)

        await manager.validate_session(created.session_id)

        last_active = repo._sessions[created.session_id].get("last_active_at")
        assert last_active is not None
        assert last_active >= before


class TestRevokeSession:
    @pytest.mark.asyncio
    async def test_revoke_deactivates_session(self) -> None:
        manager, repo = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        await manager.revoke_session(created.session_id)
        assert repo._sessions[created.session_id]["is_active"] is False

    @pytest.mark.asyncio
    async def test_revoke_session_returns_true(self) -> None:
        manager, _ = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        result = await manager.revoke_session(created.session_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_all_deactivates_all_user_sessions(self) -> None:
        manager, repo = _make_manager()
        ids = []
        for i in range(3):
            s = await manager.create_session("u", {"n": str(i)})
            ids.append(s.session_id)

        await manager.revoke_all_sessions("u")

        for sid in ids:
            assert repo._sessions[sid]["is_active"] is False

    @pytest.mark.asyncio
    async def test_revoke_all_does_not_affect_other_users(self) -> None:
        manager, repo = _make_manager()
        s_a = await manager.create_session("user-a", _FINGERPRINT_A)
        s_b = await manager.create_session("user-b", _FINGERPRINT_B)

        await manager.revoke_all_sessions("user-a")

        assert repo._sessions[s_a.session_id]["is_active"] is False
        assert repo._sessions[s_b.session_id].get("is_active", True) is True


class TestGetSession:
    @pytest.mark.asyncio
    async def test_get_session_returns_none_when_expired(self) -> None:
        manager, repo = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        repo._sessions[created.session_id]["expires_at"] = (
            datetime.now(UTC) - timedelta(seconds=1)
        )
        result = await manager.get_session(created.session_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_returns_session_without_touching_activity(self) -> None:
        manager, repo = _make_manager()
        created = await manager.create_session("u", _FINGERPRINT_A)
        original_last_active = repo._sessions[created.session_id].get("last_active_at")

        result = await manager.get_session(created.session_id)
        assert result is not None
        # get_session does NOT call update_activity
        current_last_active = repo._sessions[created.session_id].get("last_active_at")
        assert current_last_active == original_last_active
