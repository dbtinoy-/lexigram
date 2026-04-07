"""Collaborative editing support for lexigram-admin.

Provides:

* :class:`EditLock` — per-record optimistic locking (prevents two users from
  editing the same record simultaneously)
* :class:`PresenceTracker` — tracks who is currently viewing or editing a
  resource record
* :class:`CollaborativeEditingService` — orchestrates locks + presence,
  emitting change notifications when a record is saved by another user

This module integrates with the existing
:mod:`lexigram.admin.services.realtime` WebSocket layer to push live updates
to connected users.

The edit lock store is provided via constructor injection as a
:class:`~lexigram.contracts.core.stores.LockStoreProtocol`.  In production
this is backed by a persistent distributed store (e.g. SQL advisory locks or
Redis).  In tests, pass a :class:`FakeLockStore` conforming to the protocol.

Usage::

    from lexigram.admin.services.collaborative import CollaborativeEditingService

    svc = CollaborativeEditingService(lock_store=lock_store)

    # Acquire edit lock (raises LockConflictError if another user holds it)
    lock = await svc.acquire_lock("user", "record-id", user_id="alice")

    # Update presence (call on page load / heartbeat)
    await svc.update_presence("user", "record-id", user_id="alice", action="editing")

    # List who else is viewing
    viewers = svc.get_presence("user", "record-id")

    # Notify all viewers that the record changed
    await svc.notify_change("user", "record-id", changed_by="alice")

    # Release lock when done
    await svc.release_lock("user", "record-id", user_id="alice")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from lexigram.contracts.core.stores import LockStoreProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.services.realtime import RealtimeService

logger = get_logger(__name__)

_DEFAULT_LOCK_TTL_SECONDS = 300  # 5 minutes


@dataclass
class EditLock:
    """An exclusive edit lock on a resource record.

    Attributes:
        resource_type: Resource name (e.g. ``"user"``).
        record_id: Record identifier.
        user_id: Holder of the lock.
        acquired_at: UTC timestamp when the lock was acquired.
        expires_at: UTC timestamp when the lock auto-expires.
        lock_id: Unique identifier for this lock instance.
    """

    resource_type: str
    record_id: str
    user_id: str
    acquired_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(
        default_factory=lambda: (
            datetime.now(UTC) + timedelta(seconds=_DEFAULT_LOCK_TTL_SECONDS)
        )
    )
    lock_id: str = field(default_factory=lambda: "")

    def __post_init__(self) -> None:
        if not self.lock_id:
            import uuid

            self.lock_id = str(uuid.uuid4())[:8]

    @property
    def is_expired(self) -> bool:
        """Return ``True`` if the lock has passed its TTL."""
        return datetime.now(UTC) >= self.expires_at

    def refresh(self, ttl_seconds: int = _DEFAULT_LOCK_TTL_SECONDS) -> None:
        """Extend the lock expiry by *ttl_seconds* from now."""
        self.expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)


@dataclass
class PresenceEntry:
    """A single user's presence on a resource record.

    Attributes:
        user_id: User identifier.
        resource_type: Resource name.
        record_id: Record identifier.
        action: ``"viewing"`` or ``"editing"``.
        last_seen: UTC timestamp of last heartbeat.
        display_name: Optional human-readable name for the UI.
    """

    user_id: str
    resource_type: str
    record_id: str
    action: str = "viewing"
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    display_name: str = ""

    @property
    def is_stale(self) -> bool:
        """Return ``True`` if no heartbeat in the last 60 seconds."""
        return (datetime.now(UTC) - self.last_seen).total_seconds() > 60


class LockConflictError(RuntimeError):
    """Raised when trying to acquire a lock already held by another user."""

    _code: str = "LEX_ERR_ADMIN_026"

    def __init__(self, holder_id: str, expires_at: datetime) -> None:
        self.holder_id = holder_id
        self.expires_at = expires_at
        super().__init__(
            f"Record is locked by '{holder_id}' until {expires_at.isoformat()}"
        )


@inject
class CollaborativeEditingService:
    """Manages edit locks, presence, and change notifications.

    Edit lock coordination is delegated to an injected
    :class:`~lexigram.contracts.core.stores.LockStoreProtocol`, allowing
    distributed deployments to use a shared persistent store (Redis, SQL
    advisory locks, etc.) without this service knowing the implementation.
    Rich lock metadata (:class:`EditLock`) is kept in-process as a local
    cache; the store is the authoritative source for *whether* a lock is held.

    Args:
        lock_store: Injected distributed lock store.
        realtime_service: Optional
            :class:`~lexigram.admin.services.realtime.RealtimeDataService`
            instance.  When provided, ``notify_change`` broadcasts over
            WebSocket to connected users.
        lock_ttl_seconds: How long (in seconds) an edit lock remains valid
            without being refreshed.
    """

    def __init__(
        self,
        lock_store: LockStoreProtocol,
        realtime_service: RealtimeService | None = None,
        lock_ttl_seconds: int = _DEFAULT_LOCK_TTL_SECONDS,
    ) -> None:
        self._lock_store = lock_store
        self._realtime = realtime_service
        self._lock_ttl = lock_ttl_seconds
        # Local metadata cache: key "type:id" → EditLock.
        # The distributed store is authoritative for coordination; this dict
        # stores the holder identity and expiry so we can surface rich errors.
        self._lock_metadata: dict[str, EditLock] = {}
        self._presence: dict[
            str, dict[str, PresenceEntry]
        ] = {}  # key: "type:id" → {user_id: entry}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_key(resource_type: str, record_id: str) -> str:
        return f"{resource_type}:{record_id}"

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    async def acquire_lock(
        self,
        resource_type: str,
        record_id: str,
        *,
        user_id: str,
    ) -> EditLock:
        """Acquire an exclusive edit lock on a record.

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
            user_id: User attempting to acquire the lock.

        Returns:
            The acquired :class:`EditLock`.

        Raises:
            LockConflictError: If another user holds a non-expired lock.
        """
        key = self._record_key(resource_type, record_id)
        existing = self._lock_metadata.get(key)

        if existing and not existing.is_expired:
            if existing.user_id == user_id:
                # Refresh own lock in the store and update local metadata.
                await self._lock_store.extend(key, user_id, self._lock_ttl)
                existing.refresh(self._lock_ttl)
                return existing
            raise LockConflictError(existing.user_id, existing.expires_at)

        if existing and existing.is_expired:
            # Best-effort release of the stale entry from the store.
            await self._lock_store.release(key, existing.user_id)
            del self._lock_metadata[key]

        acquired = await self._lock_store.acquire(key, user_id, self._lock_ttl)
        if not acquired:
            # Another process holds the lock; we don't have local metadata for it.
            raise LockConflictError(
                "unknown",
                datetime.now(UTC) + timedelta(seconds=self._lock_ttl),
            )

        lock = EditLock(
            resource_type=resource_type,
            record_id=str(record_id),
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._lock_ttl),
        )
        self._lock_metadata[key] = lock
        logger.debug(
            "lock_acquired",
            user_id=user_id,
            resource_type=resource_type,
            record_id=record_id,
        )
        return lock

    async def release_lock(
        self,
        resource_type: str,
        record_id: str,
        *,
        user_id: str,
    ) -> bool:
        """Release a lock held by *user_id*.

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
            user_id: User releasing the lock.

        Returns:
            ``True`` if released, ``False`` if lock not found or belongs to
            another user.
        """
        key = self._record_key(resource_type, record_id)
        lock = self._lock_metadata.get(key)
        if lock is None:
            return False
        if lock.user_id != user_id:
            logger.warning(
                "lock_release_wrong_user",
                user_id=user_id,
                holder_id=lock.user_id,
                resource_type=resource_type,
                record_id=record_id,
            )
            return False
        # Best-effort release from the distributed store; always clean local metadata.
        await self._lock_store.release(key, user_id)
        del self._lock_metadata[key]
        logger.debug(
            "lock_released",
            user_id=user_id,
            resource_type=resource_type,
            record_id=record_id,
        )
        return True

    def get_lock(self, resource_type: str, record_id: str) -> EditLock | None:
        """Return the active lock for a record, or ``None``.

        Expired locks are evicted from local metadata on access.

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
        """
        key = self._record_key(resource_type, record_id)
        lock = self._lock_metadata.get(key)
        if lock and lock.is_expired:
            del self._lock_metadata[key]
            return None
        return lock

    def is_locked(self, resource_type: str, record_id: str) -> bool:
        """Return ``True`` if the record has an active lock."""
        return self.get_lock(resource_type, record_id) is not None

    def is_locked_by(self, resource_type: str, record_id: str, *, user_id: str) -> bool:
        """Return ``True`` if the record is locked by *user_id*."""
        lock = self.get_lock(resource_type, record_id)
        return lock is not None and lock.user_id == user_id

    # ------------------------------------------------------------------
    # Presence
    # ------------------------------------------------------------------

    async def update_presence(
        self,
        resource_type: str,
        record_id: str,
        *,
        user_id: str,
        action: str = "viewing",
        display_name: str = "",
    ) -> PresenceEntry:
        """Record that *user_id* is currently on *resource_type/record_id*.

        Call this on page load and periodically as a heartbeat (≤30s).

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
            user_id: User identifier.
            action: ``"viewing"`` or ``"editing"``.
            display_name: Optional human-readable name.

        Returns:
            Updated :class:`PresenceEntry`.
        """
        key = self._record_key(resource_type, record_id)
        user_map = self._presence.setdefault(key, {})
        entry = user_map.get(user_id)
        if entry:
            entry.action = action
            entry.last_seen = datetime.now(UTC)
            if display_name:
                entry.display_name = display_name
        else:
            entry = PresenceEntry(
                user_id=user_id,
                resource_type=resource_type,
                record_id=str(record_id),
                action=action,
                display_name=display_name,
            )
            user_map[user_id] = entry
        return entry

    async def leave(self, resource_type: str, record_id: str, *, user_id: str) -> None:
        """Remove a user from the presence tracking for a record.

        Also releases any lock held by the user.

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
            user_id: User who left.
        """
        key = self._record_key(resource_type, record_id)
        user_map = self._presence.get(key, {})
        user_map.pop(user_id, None)
        # Also release any lock
        await self.release_lock(resource_type, record_id, user_id=user_id)

    def get_presence(
        self,
        resource_type: str,
        record_id: str,
        *,
        exclude_user: str | None = None,
    ) -> list[PresenceEntry]:
        """Return active (non-stale) presence entries for a record.

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
            exclude_user: Optionally exclude one user (e.g. self).

        Returns:
            List of :class:`PresenceEntry` objects sorted by ``last_seen`` desc.
        """
        key = self._record_key(resource_type, record_id)
        entries = [
            e
            for e in self._presence.get(key, {}).values()
            if not e.is_stale and (exclude_user is None or e.user_id != exclude_user)
        ]
        return sorted(entries, key=lambda e: e.last_seen, reverse=True)

    # ------------------------------------------------------------------
    # Change notifications
    # ------------------------------------------------------------------

    async def notify_change(
        self,
        resource_type: str,
        record_id: str,
        *,
        changed_by: str,
        change_type: str = "update",
    ) -> int:
        """Notify all presence-tracked viewers that a record was changed.

        Sends a JSON WebSocket message via the realtime service (when wired).
        Viewers can use this to trigger a soft refresh of the record.

        Args:
            resource_type: Resource name.
            record_id: Record identifier.
            changed_by: User who made the change.
            change_type: ``"update"``, ``"delete"``, or ``"restore"``.

        Returns:
            Number of users notified.
        """
        viewers = self.get_presence(resource_type, record_id, exclude_user=changed_by)
        if not viewers or self._realtime is None:
            return len(viewers)

        import lexigram.serialization as json

        message = json.dumps(
            {
                "type": "record_changed",
                "resource_type": resource_type,
                "record_id": str(record_id),
                "changed_by": changed_by,
                "change_type": change_type,
            }
        )

        notified = 0
        for entry in viewers:
            try:
                await self._realtime.broadcast_to_user(entry.user_id, message)  # type: ignore[attr-defined]
                notified += 1
            except Exception:  # noqa: BLE001
                pass

        return notified


__all__ = [
    "CollaborativeEditingService",
    "EditLock",
    "LockConflictError",
    "PresenceEntry",
]
