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

import asyncio
from collections.abc import Collection
import copy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

from lexigram.serialization import dumps_str, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

__all__ = [
    "InMemorySettingsSnapshotStore",
    "SettingsRollback",
    "SettingsSnapshot",
    "SettingsSnapshotService",
    "SqlSettingsSnapshotStore",
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
        unset_keys: Non-secret keys that were inherited rather than persisted.
    """

    snapshot_id: str
    namespace: str
    tenant_id: str | None
    values: dict[str, Any]
    skipped_secrets: tuple[str, ...] = ()
    actor_id: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    comment: str = ""
    # Effective values are shown in history, but a rollback also needs to
    # remember which non-secret values were absent from persistence. Without
    # this distinction restoring a snapshot would materialize model defaults.
    unset_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class SettingsRollback:
    """Safe rollback payload, including exact persisted-key ownership."""

    values: dict[str, Any]
    unset_keys: frozenset[str] = frozenset()


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


class SqlSettingsSnapshotStore:
    """Durable snapshot store backed by the configured database provider.

    The table is created lazily, matching the admin settings service. Values
    arrive here only after :class:`SettingsSnapshotService` has removed secret
    keys; this adapter has no API for capturing a raw config model.
    """

    _TABLE = "admin_settings_snapshots"

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        *,
        max_per_namespace: int = 20,
    ) -> None:
        self._db = db
        self._initialized = False
        self._has_unset_keys = True
        self._init_lock = asyncio.Lock()
        self.max_per_namespace = max(1, int(max_per_namespace))

    async def _ensure_table(self) -> None:
        """Create the snapshot table and migrate older installations once."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await self._db.execute(
                f"""CREATE TABLE IF NOT EXISTS {self._TABLE} (
                    snapshot_id VARCHAR(255) PRIMARY KEY,
                    namespace VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    values_json TEXT NOT NULL,
                    skipped_secrets TEXT NOT NULL,
                    actor_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    comment TEXT NOT NULL,
                    unset_keys TEXT NOT NULL DEFAULT '[]'
                )""",  # noqa: S608 — table name is a module constant
                [],
            )
            # R57 adds ownership-preserving rollback metadata. Existing
            # deployments may already have the application-owned table, so
            # add the nullable-compatible column instead of requiring a
            # destructive migration. The fallback keeps old read-only
            # databases usable if schema alteration is unavailable.
            try:
                await self._db.execute(
                    f"SELECT unset_keys FROM {self._TABLE} LIMIT 1",  # noqa: S608 — table constant
                    [],
                )
            except Exception:  # noqa: BLE001 — migration probe is backend-specific
                try:
                    await self._db.execute(
                        f"ALTER TABLE {self._TABLE} ADD COLUMN unset_keys TEXT NOT NULL DEFAULT '[]'",  # noqa: S608 — table constant
                        [],
                    )
                except Exception:  # noqa: BLE001 — legacy schema remains readable
                    self._has_unset_keys = False
            self._initialized = True

    def _select_columns(self) -> str:
        """Return the durable columns supported by this database schema."""
        columns = (
            "snapshot_id, namespace, tenant_id, values_json, "
            "skipped_secrets, actor_id, created_at, comment"
        )
        return f"{columns}, unset_keys" if self._has_unset_keys else columns

    @staticmethod
    def _created_at(value: Any) -> datetime:
        """Normalize provider timestamp values to timezone-aware UTC."""
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                pass
        return datetime.now(UTC)

    @classmethod
    def _from_row(cls, row: dict[str, Any]) -> SettingsSnapshot:
        """Convert a database row to the domain snapshot shape."""
        try:
            values = loads_str(row.get("values_json") or "{}")
        except (TypeError, ValueError):
            values = {}
        try:
            skipped = loads_str(row.get("skipped_secrets") or "[]")
        except (TypeError, ValueError):
            skipped = []
        try:
            unset_keys = loads_str(row.get("unset_keys") or "[]")
        except (TypeError, ValueError):
            unset_keys = []
        return SettingsSnapshot(
            snapshot_id=str(row.get("snapshot_id", "")),
            namespace=str(row.get("namespace", "")),
            tenant_id=row.get("tenant_id"),
            values=values if isinstance(values, dict) else {},
            skipped_secrets=tuple(str(item) for item in skipped if item is not None),
            actor_id=str(row.get("actor_id", "system")),
            created_at=cls._created_at(row.get("created_at")),
            comment=str(row.get("comment", "")),
            unset_keys=tuple(str(item) for item in unset_keys if item is not None),
        )

    async def save(self, snapshot: SettingsSnapshot) -> None:
        """Persist and trim one snapshot."""
        await self._ensure_table()
        if self._has_unset_keys:
            insert_sql = f"""INSERT INTO {self._TABLE}
                (snapshot_id, namespace, tenant_id, values_json,
                 skipped_secrets, actor_id, created_at, comment, unset_keys)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""  # noqa: S608 — table constant
            insert_params = [
                snapshot.snapshot_id,
                snapshot.namespace,
                snapshot.tenant_id,
                dumps_str(snapshot.values, sort_keys=True, default=str),
                dumps_str(list(snapshot.skipped_secrets)),
                snapshot.actor_id,
                snapshot.created_at.isoformat(),
                snapshot.comment,
                dumps_str(list(snapshot.unset_keys)),
            ]
        else:
            insert_sql = f"""INSERT INTO {self._TABLE}
                (snapshot_id, namespace, tenant_id, values_json,
                 skipped_secrets, actor_id, created_at, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""  # noqa: S608 — table constant
            insert_params = [
                snapshot.snapshot_id,
                snapshot.namespace,
                snapshot.tenant_id,
                dumps_str(snapshot.values, sort_keys=True, default=str),
                dumps_str(list(snapshot.skipped_secrets)),
                snapshot.actor_id,
                snapshot.created_at.isoformat(),
                snapshot.comment,
            ]
        await self._db.execute(insert_sql, insert_params)
        tenant_clause = (
            "tenant_id IS NULL" if snapshot.tenant_id is None else "tenant_id = ?"
        )
        params: list[Any] = [snapshot.namespace]
        if snapshot.tenant_id is not None:
            params.append(snapshot.tenant_id)
        result = await self._db.execute(
            f"SELECT snapshot_id FROM {self._TABLE} "
            f"WHERE namespace = ? AND {tenant_clause} "
            "ORDER BY created_at DESC, snapshot_id DESC",
            params,
        )  # noqa: S608 — table constant
        rows = getattr(result, "rows", []) or []
        for row in rows[self.max_per_namespace :]:
            snapshot_id = row.get("snapshot_id")
            if snapshot_id:
                await self._db.execute(
                    f"DELETE FROM {self._TABLE} WHERE snapshot_id = ?",  # noqa: S608 — table constant
                    [snapshot_id],
                )

    async def list_for_namespace(
        self, namespace: str, tenant_id: str | None, *, limit: int = 20
    ) -> list[SettingsSnapshot]:
        """List snapshots newest first with a bounded caller limit."""
        await self._ensure_table()
        safe_limit = max(1, min(int(limit), 100))
        if tenant_id is None:
            query = (
                f"SELECT {self._select_columns()} FROM {self._TABLE} "
                "WHERE namespace = ? AND tenant_id IS NULL "
                f"ORDER BY created_at DESC, snapshot_id DESC LIMIT {safe_limit}"
            )
            params: list[Any] = [namespace]
        else:
            query = (
                f"SELECT {self._select_columns()} FROM {self._TABLE} "
                "WHERE namespace = ? AND tenant_id = ? "
                f"ORDER BY created_at DESC, snapshot_id DESC LIMIT {safe_limit}"
            )
            params = [namespace, tenant_id]
        result = await self._db.execute(query, params)  # noqa: S608 — table constant
        return [self._from_row(row) for row in (getattr(result, "rows", []) or [])]

    async def get(self, snapshot_id: str) -> SettingsSnapshot | None:
        """Fetch one snapshot by its opaque identifier."""
        await self._ensure_table()
        result = await self._db.execute(
            f"SELECT {self._select_columns()} FROM {self._TABLE} WHERE snapshot_id = ?",  # noqa: S608 — table constant
            [snapshot_id],
        )
        rows = getattr(result, "rows", []) or []
        return self._from_row(rows[0]) if rows else None


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
        secret_keys: Collection[str] | None = None,
        tenant_id: str | None = None,
        actor_id: str = "system",
        comment: str = "",
        unset_keys: Collection[str] | None = None,
    ) -> SettingsSnapshot:
        """Record the state of a namespace before it is changed.

        Args:
            namespace: Configuration namespace.
            values: Effective values about to be replaced.
            secret_keys: Keys whose values must not be captured.
            tenant_id: Tenant scope, or ``None`` for global settings.
            actor_id: Principal making the change.
            comment: Optional note.
            unset_keys: Non-secret keys whose effective values came from the
                node default rather than persisted configuration.

        Returns:
            The stored :class:`SettingsSnapshot`.
        """
        secrets = set(secret_keys or ())
        from lexigram.admin.settings.application import redact_config_value

        captured = {
            key: redact_config_value(val, key=str(key))
            for key, val in values.items()
            if key not in secrets
        }
        skipped = tuple(sorted(key for key in values if key in secrets))
        unset = tuple(
            sorted(
                key
                for key in (unset_keys or ())
                if key in captured and key not in secrets
            )
        )

        snapshot = SettingsSnapshot(
            snapshot_id=self._new_id(),
            namespace=namespace,
            tenant_id=tenant_id,
            values=captured,
            skipped_secrets=skipped,
            actor_id=actor_id,
            comment=comment,
            unset_keys=unset,
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

    async def rollback_state(
        self,
        snapshot_id: str,
        *,
        namespace: str | None = None,
        tenant_id: str | None = None,
    ) -> SettingsRollback | None:
        """Return safe values plus exact persisted-key ownership for restore.

        Does not write anything: the caller re-submits the values through the
        normal save path so validation, permissions, and auditing still run.
        A namespace and tenant check is applied before any payload is exposed.

        Args:
            snapshot_id: Snapshot to restore.
            namespace: When given, the snapshot must belong to it.
            tenant_id: When *namespace* is given, the tenant must also match.

        Returns:
            A copied rollback payload, or ``None`` when the snapshot is
            missing or belongs to a different namespace or tenant.
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
        if (
            namespace is None
            and tenant_id is not None
            and snapshot.tenant_id != tenant_id
        ):
            return None
        return SettingsRollback(
            values=copy.deepcopy(snapshot.values),
            unset_keys=frozenset(snapshot.unset_keys),
        )

    async def rollback_values(
        self,
        snapshot_id: str,
        *,
        namespace: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Return only the captured values for legacy callers.

        New restore paths should use :meth:`rollback_state` so they can also
        restore whether a key was absent from persistence.
        """
        state = await self.rollback_state(
            snapshot_id,
            namespace=namespace,
            tenant_id=tenant_id,
        )
        return dict(state.values) if state is not None else None
