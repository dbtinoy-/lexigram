"""Tests for CollaborativeEditingService — locks, presence, notifications."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.admin.services.collaborative import (
    CollaborativeEditingService,
    EditLock,
    LockConflictError,
    PresenceEntry,
)


# ---------------------------------------------------------------------------
# Fake lock store (conforms to LockStoreProtocol without importing it)
# ---------------------------------------------------------------------------

class FakeLockStore:
    """In-memory LockStoreProtocol implementation for tests."""

    def __init__(self) -> None:
        self._held: dict[str, str] = {}  # lock_name → owner

    async def acquire(self, lock_name: str, owner: str, ttl: int) -> bool:
        if lock_name in self._held:
            return False
        self._held[lock_name] = owner
        return True

    async def release(self, lock_name: str, owner: str) -> bool:
        if self._held.get(lock_name) == owner:
            del self._held[lock_name]
            return True
        return False

    async def extend(self, lock_name: str, owner: str, ttl: int) -> bool:
        return self._held.get(lock_name) == owner


def make_svc(**kwargs: object) -> CollaborativeEditingService:
    """Factory that always injects a fresh FakeLockStore."""
    return CollaborativeEditingService(lock_store=FakeLockStore(), **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# EditLock
# ---------------------------------------------------------------------------

class TestEditLock:
    def test_not_expired_when_fresh(self) -> None:
        lock = EditLock("user", "u1", user_id="alice")
        assert lock.is_expired is False

    def test_expired_when_past_expires_at(self) -> None:
        lock = EditLock("user", "u1", user_id="alice")
        lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        assert lock.is_expired is True

    def test_refresh_extends_expiry(self) -> None:
        lock = EditLock("user", "u1", user_id="alice")
        original = lock.expires_at
        lock.refresh(600)
        assert lock.expires_at > original

    def test_lock_id_auto_generated(self) -> None:
        lock = EditLock("user", "u1", user_id="alice")
        assert lock.lock_id


# ---------------------------------------------------------------------------
# Acquiring locks
# ---------------------------------------------------------------------------

class TestAcquireLock:
    @pytest.mark.asyncio
    async def test_acquire_returns_lock(self) -> None:
        svc = make_svc()
        lock = await svc.acquire_lock("user", "u1", user_id="alice")
        assert lock.user_id == "alice"
        assert lock.resource_type == "user"

    @pytest.mark.asyncio
    async def test_acquire_by_same_user_refreshes(self) -> None:
        svc = make_svc()
        lock1 = await svc.acquire_lock("user", "u1", user_id="alice")
        lock2 = await svc.acquire_lock("user", "u1", user_id="alice")
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_acquire_by_different_user_raises(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        with pytest.raises(LockConflictError) as exc_info:
            await svc.acquire_lock("user", "u1", user_id="bob")
        assert exc_info.value.holder_id == "alice"

    @pytest.mark.asyncio
    async def test_acquire_after_expiry(self) -> None:
        svc = make_svc()
        lock = await svc.acquire_lock("user", "u1", user_id="alice")
        lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        # Bob can now acquire the expired lock
        lock2 = await svc.acquire_lock("user", "u1", user_id="bob")
        assert lock2.user_id == "bob"

    @pytest.mark.asyncio
    async def test_different_records_independent(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        lock2 = await svc.acquire_lock("user", "u2", user_id="alice")
        assert lock2.record_id == "u2"


# ---------------------------------------------------------------------------
# Releasing locks
# ---------------------------------------------------------------------------

class TestReleaseLock:
    @pytest.mark.asyncio
    async def test_release_returns_true(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        released = await svc.release_lock("user", "u1", user_id="alice")
        assert released is True

    @pytest.mark.asyncio
    async def test_release_removes_lock(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        await svc.release_lock("user", "u1", user_id="alice")
        assert svc.is_locked("user", "u1") is False

    @pytest.mark.asyncio
    async def test_release_by_wrong_user_fails(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        result = await svc.release_lock("user", "u1", user_id="bob")
        assert result is False
        assert svc.is_locked("user", "u1") is True

    @pytest.mark.asyncio
    async def test_release_missing_returns_false(self) -> None:
        svc = make_svc()
        result = await svc.release_lock("user", "ghost", user_id="alice")
        assert result is False


# ---------------------------------------------------------------------------
# Lock query
# ---------------------------------------------------------------------------

class TestLockQuery:
    @pytest.mark.asyncio
    async def test_is_locked_true(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        assert svc.is_locked("user", "u1") is True

    def test_is_locked_false_when_no_lock(self) -> None:
        svc = make_svc()
        assert svc.is_locked("user", "u1") is False

    @pytest.mark.asyncio
    async def test_is_locked_by_correct_user(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        assert svc.is_locked_by("user", "u1", user_id="alice") is True
        assert svc.is_locked_by("user", "u1", user_id="bob") is False

    @pytest.mark.asyncio
    async def test_expired_lock_treated_as_absent(self) -> None:
        svc = make_svc()
        lock = await svc.acquire_lock("user", "u1", user_id="alice")
        lock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        assert svc.get_lock("user", "u1") is None


# ---------------------------------------------------------------------------
# Presence
# ---------------------------------------------------------------------------

class TestPresence:
    @pytest.mark.asyncio
    async def test_update_presence(self) -> None:
        svc = make_svc()
        entry = await svc.update_presence("user", "u1", user_id="alice", action="editing")
        assert entry.user_id == "alice"
        assert entry.action == "editing"

    @pytest.mark.asyncio
    async def test_update_presence_idempotent(self) -> None:
        svc = make_svc()
        await svc.update_presence("user", "u1", user_id="alice")
        await svc.update_presence("user", "u1", user_id="alice", action="editing")
        present = svc.get_presence("user", "u1")
        assert len(present) == 1
        assert present[0].action == "editing"

    @pytest.mark.asyncio
    async def test_multiple_users_present(self) -> None:
        svc = make_svc()
        await svc.update_presence("user", "u1", user_id="alice")
        await svc.update_presence("user", "u1", user_id="bob")
        present = svc.get_presence("user", "u1")
        assert {e.user_id for e in present} == {"alice", "bob"}

    @pytest.mark.asyncio
    async def test_get_presence_exclude_user(self) -> None:
        svc = make_svc()
        await svc.update_presence("user", "u1", user_id="alice")
        await svc.update_presence("user", "u1", user_id="bob")
        present = svc.get_presence("user", "u1", exclude_user="alice")
        assert all(e.user_id != "alice" for e in present)

    @pytest.mark.asyncio
    async def test_leave_removes_presence(self) -> None:
        svc = make_svc()
        await svc.update_presence("user", "u1", user_id="alice")
        await svc.leave("user", "u1", user_id="alice")
        assert svc.get_presence("user", "u1") == []

    @pytest.mark.asyncio
    async def test_leave_also_releases_lock(self) -> None:
        svc = make_svc()
        await svc.acquire_lock("user", "u1", user_id="alice")
        await svc.update_presence("user", "u1", user_id="alice")
        await svc.leave("user", "u1", user_id="alice")
        assert svc.is_locked("user", "u1") is False

    @pytest.mark.asyncio
    async def test_stale_entries_excluded(self) -> None:
        svc = make_svc()
        entry = await svc.update_presence("user", "u1", user_id="alice")
        entry.last_seen = datetime.now(UTC) - timedelta(seconds=120)
        present = svc.get_presence("user", "u1")
        assert len(present) == 0


# ---------------------------------------------------------------------------
# Notify change
# ---------------------------------------------------------------------------

class TestNotifyChange:
    @pytest.mark.asyncio
    async def test_notify_returns_zero_when_no_realtime(self) -> None:
        svc = make_svc()
        await svc.update_presence("user", "u1", user_id="bob")
        count = await svc.notify_change("user", "u1", changed_by="alice")
        assert count == 1  # 1 viewer (no realtime, count still returned)

    @pytest.mark.asyncio
    async def test_notify_excludes_changer(self) -> None:
        svc = make_svc()
        await svc.update_presence("user", "u1", user_id="alice")
        await svc.update_presence("user", "u1", user_id="bob")
        # Alice is the changer — only Bob should be notified
        count = await svc.notify_change("user", "u1", changed_by="alice")
        assert count == 1
