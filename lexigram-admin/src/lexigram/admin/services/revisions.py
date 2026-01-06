"""Revision history service for lexigram-admin.

Stores full field snapshots on each save and provides field-by-field diff
comparison between any two revisions. Supports revert to any prior revision.

The service uses a structural ``_RevisionStore`` protocol so it works with
an in-memory store (default, zero dependencies) or a DB-backed store
injected via the DI container.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Revision:
    """A single point-in-time snapshot of a resource record.

    Attributes:
        revision_id: Unique identifier for this revision.
        resource_type: Name of the resource type (e.g. ``"user"``).
        resource_id: Identifier of the affected record.
        data: Full field snapshot at this point in time.
        actor_id: Who created this revision.
        created_at: UTC timestamp.
        comment: Optional human-readable description of the change.
    """

    revision_id: str
    resource_type: str
    resource_id: str
    data: dict[str, Any]
    actor_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    comment: str = ""


@dataclass
class FieldDiff:
    """The change for a single field between two revisions.

    Attributes:
        field_name: Name of the field that changed.
        old_value: Value in the earlier revision (``None`` if field was absent).
        new_value: Value in the later revision (``None`` if field was removed).
        changed: Whether old and new values differ.
    """

    field_name: str
    old_value: Any
    new_value: Any
    changed: bool


@dataclass
class RevisionDiff:
    """Diff result between two revisions.

    Attributes:
        from_revision: Earlier revision identifier.
        to_revision: Later revision identifier.
        fields: Per-field diff entries (only fields where ``changed=True`` by default).
        all_fields: When ``True`` all fields were included, not just changed ones.
    """

    from_revision: str
    to_revision: str
    fields: list[FieldDiff]
    all_fields: bool = False


# ---------------------------------------------------------------------------
# Storage protocol
# ---------------------------------------------------------------------------


class _RevisionStore(Protocol):
    """Minimal storage protocol for revision persistence."""

    async def save(self, revision: Revision) -> None:
        """Persist a new revision."""
        ...

    async def list_for_record(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> list[Revision]:
        """Return revisions for a record, newest-first."""
        ...

    async def get(self, revision_id: str) -> Revision | None:
        """Return a single revision by ID."""
        ...

    async def delete_for_record(self, resource_type: str, resource_id: str) -> int:
        """Delete all revisions for a record. Returns count deleted."""
        ...


# ---------------------------------------------------------------------------
# In-memory store (default — zero infra deps)
# ---------------------------------------------------------------------------


class InMemoryRevisionStore:
    """Thread-safe in-process revision store.

    Suitable for development and testing. Data is lost on restart.
    For production wire a DB-backed store via the DI container.
    """

    def __init__(self, max_per_record: int = 100) -> None:
        self._store: dict[str, list[Revision]] = {}  # key: "type:id"
        self._by_id: dict[str, Revision] = {}
        self.max_per_record = max_per_record

    def _key(self, resource_type: str, resource_id: str) -> str:
        return f"{resource_type}:{resource_id}"

    async def save(self, revision: Revision) -> None:
        """Persist revision, trimming oldest if over max_per_record."""
        k = self._key(revision.resource_type, revision.resource_id)
        bucket = self._store.setdefault(k, [])
        bucket.insert(0, revision)
        self._by_id[revision.revision_id] = revision
        if len(bucket) > self.max_per_record:
            dropped = bucket.pop()
            self._by_id.pop(dropped.revision_id, None)

    async def list_for_record(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> list[Revision]:
        """Return up to *limit* revisions, newest-first."""
        k = self._key(resource_type, resource_id)
        return self._store.get(k, [])[:limit]

    async def get(self, revision_id: str) -> Revision | None:
        return self._by_id.get(revision_id)

    async def delete_for_record(self, resource_type: str, resource_id: str) -> int:
        k = self._key(resource_type, resource_id)
        revisions = self._store.pop(k, [])
        for rev in revisions:
            self._by_id.pop(rev.revision_id, None)
        return len(revisions)


# ---------------------------------------------------------------------------
# RevisionService
# ---------------------------------------------------------------------------


class RevisionService:
    """Manages resource revision snapshots with diff and revert support.

    Args:
        store: Revision store implementation. Defaults to
            :class:`InMemoryRevisionStore`.
        max_revisions: Maximum revisions retained per record (forwarded to
            :class:`InMemoryRevisionStore` if no store is provided).
    """

    def __init__(
        self,
        store: _RevisionStore | None = None,
        max_revisions: int = 100,
    ) -> None:
        self._store: _RevisionStore = store or InMemoryRevisionStore(
            max_per_record=max_revisions
        )
        self._counter: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _new_id(self) -> str:
        self._counter += 1
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"rev-{ts}-{self._counter}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record(
        self,
        resource_type: str,
        resource_id: str,
        data: dict[str, Any],
        *,
        actor_id: str = "system",
        comment: str = "",
    ) -> Revision:
        """Create and persist a new revision snapshot.

        Call this *after* a successful save so the snapshot reflects the
        committed state.

        Args:
            resource_type: Resource name (e.g. ``"user"``).
            resource_id: Record identifier.
            data: Full field snapshot.
            actor_id: Principal who triggered the change.
            comment: Optional human-readable note.

        Returns:
            The newly created :class:`Revision`.
        """
        revision = Revision(
            revision_id=self._new_id(),
            resource_type=resource_type,
            resource_id=str(resource_id),
            data=dict(data),
            actor_id=actor_id,
            comment=comment,
        )
        await self._store.save(revision)
        return revision

    async def list_revisions(
        self,
        resource_type: str,
        resource_id: str,
        *,
        limit: int = 50,
    ) -> list[Revision]:
        """Return revisions for a record, newest-first.

        Args:
            resource_type: Resource name.
            resource_id: Record identifier.
            limit: Maximum number of revisions to return.

        Returns:
            List of :class:`Revision` objects.
        """
        return await self._store.list_for_record(
            resource_type, str(resource_id), limit=limit
        )

    async def get_revision(self, revision_id: str) -> Revision | None:
        """Fetch a single revision by ID.

        Args:
            revision_id: The revision identifier.

        Returns:
            :class:`Revision` or ``None`` if not found.
        """
        return await self._store.get(revision_id)

    async def diff(
        self,
        revision_id_a: str,
        revision_id_b: str,
        *,
        include_unchanged: bool = False,
    ) -> RevisionDiff | None:
        """Compute a field-by-field diff between two revisions.

        Args:
            revision_id_a: Earlier (or baseline) revision.
            revision_id_b: Later revision.
            include_unchanged: When ``True`` all fields are included, not just
                those that changed.

        Returns:
            :class:`RevisionDiff` or ``None`` if either revision is not found.
        """
        rev_a = await self._store.get(revision_id_a)
        rev_b = await self._store.get(revision_id_b)
        if rev_a is None or rev_b is None:
            return None

        all_keys = set(rev_a.data) | set(rev_b.data)
        diffs: list[FieldDiff] = []
        for key in sorted(all_keys):
            old = rev_a.data.get(key)
            new = rev_b.data.get(key)
            changed = old != new
            if include_unchanged or changed:
                diffs.append(
                    FieldDiff(
                        field_name=key, old_value=old, new_value=new, changed=changed
                    )
                )

        return RevisionDiff(
            from_revision=revision_id_a,
            to_revision=revision_id_b,
            fields=diffs,
            all_fields=include_unchanged,
        )

    async def revert_data(self, revision_id: str) -> dict[str, Any] | None:
        """Return the data snapshot from a prior revision, ready to apply.

        Does **not** persist anything — callers are responsible for passing
        the returned data to their update handler (and then calling
        :meth:`record` to snapshot the revert).

        Args:
            revision_id: The revision to revert to.

        Returns:
            Field snapshot dict or ``None`` if revision not found.
        """
        revision = await self._store.get(revision_id)
        return dict(revision.data) if revision else None

    async def purge(self, resource_type: str, resource_id: str) -> int:
        """Delete all revisions for a record.

        Args:
            resource_type: Resource name.
            resource_id: Record identifier.

        Returns:
            Number of revisions deleted.
        """
        return await self._store.delete_for_record(resource_type, str(resource_id))


__all__ = [
    "FieldDiff",
    "InMemoryRevisionStore",
    "Revision",
    "RevisionDiff",
    "RevisionService",
]
