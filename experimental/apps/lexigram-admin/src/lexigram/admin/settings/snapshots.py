"""Point-in-time snapshots of configuration values, with rollback.

Settings saves were previously irreversible: a mistaken change to a
namespace could only be undone by remembering the old values by hand. This
records the state before each successful save so an operator can inspect
recent changes and roll one back.

Snapshots are scoped by namespace and tenant. Secret values are never
captured — a snapshot is metadata an operator reads, and reversing a secret
would require storing it in plaintext. Secrets are listed as skipped so a
rollback never silently claims to have restored one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

__all__ = [
    "InMemorySettingsSnapshotStore",
    "SettingsSnapshot",
    "SettingsSnapshotService",
]


@dataclass(frozen=True)
class SettingsSnapshot:
    """The values of one configuration namespace at a point in time.

    Attributes:
        snapshot_id: Unique identifier.
        namespace: Configuration namespace the values belong to.
        tenant_id: Tenant scope, or ``None`` for global settings.
        values: Non-secret values captured before the change.
        skipped_secrets: Secret keys deliberately not captured.
        actor_id: Who triggered the change this snapshot precedes.
        created_at: UTC timestamp.
        comment: Optional human-readable note.
    """

    snapshot_id: str
    namespace: str
    tenant_id: str | None
    values: dict[str, Any]
    skipped_secrets: tuple[str, ...] = ()
    actor_id: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    comment: str = ""


class _SnapshotStore(Protocol):
    """Minimal persistence protocol for settings snapshots."""

    async def save(self, snapshot: SettingsSnapshot) -> None:
        """Persist a snapshot."""
        ...

    async def list_for_namespace(
        self, namespace: str, tenant_id: str | None, *, limit: int = 20
    ) -> list[SettingsSnapshot]:
        """Return snapshots for a namespace, newest first."""
        ...

    async def get(self, snapshot_id: str) -> SettingsSnapshot | None:
        """Return a snapshot by identifier."""
        ...


class InMemorySettingsSnapshotStore:
    """In-process snapshot store.

    Suitable for development and single-process deployments. History is lost
    on restart; wire a durable store via DI for production use.
    """

    def __init__(self, max_per_namespace: int = 20) -> None:
        self._buckets: dict[tuple[str, str | None], list[SettingsSnapshot]] = {}
        self._by_id: dict[str, SettingsSnapshot] = {}
        self.max_per_namespace = max_per_namespace

    async def save(self, snapshot: SettingsSnapshot) -> None:
        """Persist a snapshot, trimming the oldest beyond the retention cap."""
        key = (snapshot.namespace, snapshot.tenant_id)
        bucket = self._buckets.setdefault(key, [])
        bucket.insert(0, snapshot)
        self._by_id[snapshot.snapshot_id] = snapshot
        while len(bucket) > self.max_per_namespace:
            dropped = bucket.pop()
            self._by_id.pop(dropped.snapshot_id, None)

    async def list_for_namespace(
        self, namespace: str, tenant_id: str | None, *, limit: int = 20
    ) -> list[SettingsSnapshot]:
        """Return up to *limit* snapshots, newest first."""
        return self._buckets.get((namespace, tenant_id), [])[:limit]

    async def get(self, snapshot_id: str) -> SettingsSnapshot | None:
        """Return a snapshot by identifier, or ``None``."""
        return self._by_id.get(snapshot_id)


class SettingsSnapshotService:
    """Records settings history and resolves rollback payloads.

    Args:
        store: Snapshot persistence. Defaults to an in-memory store.
        max_per_namespace: Retention cap forwarded to the default store.
    """

    def __init__(
        self,
        store: _SnapshotStore | None = None,
        max_per_namespace: int = 20,
    ) -> None:
        self._store: _SnapshotStore = store or InMemorySettingsSnapshotStore(
            max_per_namespace=max_per_namespace
        )
        self._counter = 0

    def _new_id(self) -> str:
        self._counter += 1
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"cfg-{stamp}-{self._counter}"

    async def capture(
        self,
        namespace: str,
        values: dict[str, Any],
        *,
        secret_keys: frozenset[str] | set[str] | None = None,
        tenant_id: str | None = None,
        actor_id: str = "system",
        comment: str = "",
    ) -> SettingsSnapshot:
        """Record the state of a namespace before it is changed.

        Args:
            namespace: Configuration namespace.
            values: Effective values about to be replaced.
            secret_keys: Keys whose values must not be captured.
            tenant_id: Tenant scope, or ``None`` for global settings.
            actor_id: Principal making the change.
            comment: Optional note.

        Returns:
            The stored :class:`SettingsSnapshot`.
        """
        secrets = set(secret_keys or ())
        captured = {key: val for key, val in values.items() if key not in secrets}
        skipped = tuple(sorted(key for key in values if key in secrets))

        snapshot = SettingsSnapshot(
            snapshot_id=self._new_id(),
            namespace=namespace,
            tenant_id=tenant_id,
            values=captured,
            skipped_secrets=skipped,
            actor_id=actor_id,
            comment=comment,
        )
        await self._store.save(snapshot)
        return snapshot

    async def list_history(
        self, namespace: str, tenant_id: str | None = None, *, limit: int = 20
    ) -> list[SettingsSnapshot]:
        """Return recent snapshots for a namespace, newest first."""
        return await self._store.list_for_namespace(namespace, tenant_id, limit=limit)

    async def get(self, snapshot_id: str) -> SettingsSnapshot | None:
        """Return a snapshot by identifier, or ``None``."""
        return await self._store.get(snapshot_id)

    async def rollback_values(
        self,
        snapshot_id: str,
        *,
        namespace: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the values to re-apply for a snapshot.

        Does not write anything: the caller re-submits these through the
        normal save path so validation, permissions, and auditing still run.

        Args:
            snapshot_id: Snapshot to restore.
            namespace: When given, the snapshot must belong to it.
            tenant_id: When *namespace* is given, the tenant must also match.

        Returns:
            The captured values, or ``None`` when the snapshot is missing or
            belongs to a different namespace or tenant.
        """
        snapshot = await self._store.get(snapshot_id)
        if snapshot is None:
            return None
        # A snapshot id from another namespace or tenant must never be
        # applied here; that would be a cross-tenant write via a guessed id.
        if namespace is not None and snapshot.namespace != namespace:
            return None
        if namespace is not None and snapshot.tenant_id != tenant_id:
            return None
        return dict(snapshot.values)
