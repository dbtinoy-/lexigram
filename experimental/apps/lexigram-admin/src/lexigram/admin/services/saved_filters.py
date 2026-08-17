"""Saved filter service for lexigram-admin.

Allows users to save named filter combinations per resource and quickly
re-apply them from a dropdown in the filter panel.

Filter sets are stored as JSON blobs in the admin_saved_filters table (or
in-memory when no database is configured).

Usage::

    svc = SavedFiltersService()
    await svc.save("users", "Active Admins", {"role": "admin", "is_active": "1"}, user_id="u1")
    sets = await svc.list_for_resource("users", user_id="u1")
    await svc.delete("users", "Active Admins", user_id="u1")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from lexigram import serialization as json
from lexigram.admin.exceptions import AdminError, NotFoundError
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SavedFilterSet:
    """A named filter combination saved by a user for a resource.

    Attributes:
        resource: Resource name (e.g. ``"users"``).
        name: Human-readable label for this filter set.
        filters: Mapping of field name → filter value.
        user_id: Owner of this saved filter (``None`` = shared / global).
        created_at: When the filter was saved.
    """

    resource: str
    name: str
    filters: dict[str, Any]
    user_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Storage protocol (structural)
# ---------------------------------------------------------------------------


@runtime_checkable
class _FilterRepository(Protocol):
    """Narrow structural protocol for the saved-filters storage backend."""

    async def find_many(
        self, *, limit: int = 100, offset: int = 0, **filters: Any
    ) -> list[Any]: ...

    async def create(self, data: Any) -> Any: ...

    async def delete(self, item_id: Any) -> bool: ...

    async def find_one(self, **filters: Any) -> Any | None: ...


# ---------------------------------------------------------------------------
# In-memory fallback backend
# ---------------------------------------------------------------------------


class _InMemoryFilterStore:
    """Ephemeral in-memory store used when no database backend is provided."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._next_id: int = 1

    async def find_many(
        self, *, limit: int = 100, offset: int = 0, **filters: Any
    ) -> list[Any]:
        results = []
        for rec in self._records:
            if all(rec.get(k) == v for k, v in filters.items()):
                results.append(rec)
        return results[offset : offset + limit]

    async def create(self, data: Any) -> Any:
        record = dict(data) if not isinstance(data, dict) else data
        record["id"] = self._next_id
        self._next_id += 1
        self._records.append(record)
        return record

    async def delete(self, item_id: Any) -> bool:
        before = len(self._records)
        self._records = [r for r in self._records if r.get("id") != item_id]
        return len(self._records) < before

    async def find_one(self, **filters: Any) -> Any | None:
        for rec in self._records:
            if all(rec.get(k) == v for k, v in filters.items()):
                return rec
        return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


@inject
class SavedFiltersService:
    """Manages named filter presets per resource and user.

    Args:
        repository: Optional storage backend implementing :class:`_FilterRepository`.
            Falls back to an ephemeral in-memory store when ``None``.
        max_per_user_per_resource: Maximum saved filter sets allowed per
            user × resource combination (0 = unlimited).
    """

    def __init__(
        self,
        repository: _FilterRepository | None = None,
        *,
        max_per_user_per_resource: int = 20,
    ) -> None:
        self._repo: _FilterRepository = repository or _InMemoryFilterStore()
        self._max = max_per_user_per_resource

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save(
        self,
        resource: str,
        name: str,
        filters: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> Result[SavedFilterSet, AdminError]:
        """Save a named filter set.

        If a filter set with the same ``resource``+``name``+``user_id`` already
        exists it is overwritten.

        Args:
            resource: Resource name (e.g. ``"users"``).
            name: Label for the filter set.
            filters: Field → value mapping to store.
            user_id: User who owns this preset (``None`` = global preset).

        Returns:
            ``Result[SavedFilterSet, AdminError]``.
        """
        if not name.strip():
            return Err(AdminError(message="Filter set name must not be empty"))
        if not filters:
            return Err(
                AdminError(message="Filter set must contain at least one filter")
            )

        # Enforce per-user-per-resource limit
        if self._max:
            existing = await self._repo.find_many(resource=resource, user_id=user_id)
            if len(existing) >= self._max:
                # Check if this name already exists (overwrite is fine)
                match = next((r for r in existing if r.get("name") == name), None)
                if match is None:
                    return Err(
                        AdminError(
                            message=f"Maximum of {self._max} saved filters reached for this resource"
                        )
                    )

        # Upsert: delete existing with same key before inserting
        existing_row = await self._repo.find_one(
            resource=resource, name=name, user_id=user_id
        )
        if existing_row is not None:
            row_id = existing_row.get("id")
            if row_id is not None:
                await self._repo.delete(row_id)

        now = datetime.now(UTC)
        record = {
            "resource": resource,
            "name": name,
            "filters_json": json.dumps(filters).decode()
            if isinstance(json.dumps(filters), bytes)
            else json.dumps(filters),
            "user_id": user_id,
            "created_at": now.isoformat(),
        }
        await self._repo.create(record)

        saved = SavedFilterSet(
            resource=resource,
            name=name,
            filters=filters,
            user_id=user_id,
            created_at=now,
        )
        logger.info(
            "Saved filter set: resource=%s name=%r user_id=%s", resource, name, user_id
        )
        return Ok(saved)

    async def list_for_resource(
        self,
        resource: str,
        *,
        user_id: str | None = None,
    ) -> list[SavedFilterSet]:
        """List all saved filter sets for a resource.

        Returns both the user's own presets and global (user_id=None) presets.

        Args:
            resource: Resource name.
            user_id: Return presets owned by this user plus global ones.

        Returns:
            List of :class:`SavedFilterSet` sorted by name.
        """
        rows: list[Any] = []

        # User's own presets
        if user_id is not None:
            rows.extend(await self._repo.find_many(resource=resource, user_id=user_id))

        # Global presets (shared)
        global_rows = await self._repo.find_many(resource=resource, user_id=None)
        rows.extend(global_rows)

        result: list[SavedFilterSet] = []
        for row in rows:
            try:
                filters_raw = row.get("filters_json", "{}")
                filters = (
                    json.loads(filters_raw)
                    if isinstance(filters_raw, (str, bytes))
                    else {}
                )
                created_at_raw = row.get("created_at")
                created_at = (
                    datetime.fromisoformat(created_at_raw)
                    if isinstance(created_at_raw, str)
                    else datetime.now(UTC)
                )
                result.append(
                    SavedFilterSet(
                        resource=row.get("resource", resource),
                        name=row.get("name", ""),
                        filters=filters,
                        user_id=row.get("user_id"),
                        created_at=created_at,
                    )
                )
            except (KeyError, ValueError, TypeError):
                logger.warning("Skipping malformed saved filter row: %s", row)

        return sorted(result, key=lambda s: s.name)

    async def delete(
        self,
        resource: str,
        name: str,
        *,
        user_id: str | None = None,
    ) -> Result[None, NotFoundError]:
        """Delete a saved filter set by resource + name + owner.

        Args:
            resource: Resource name.
            name: Filter set label.
            user_id: Owner user ID.

        Returns:
            ``Result[None, NotFoundError]``.
        """
        row = await self._repo.find_one(resource=resource, name=name, user_id=user_id)
        if row is None:
            return Err(
                NotFoundError(
                    message=f"Saved filter '{name}' not found for resource '{resource}'"
                )
            )

        row_id = row.get("id")
        if row_id is not None:
            await self._repo.delete(row_id)

        return Ok(None)


__all__ = [
    "SavedFilterSet",
    "SavedFiltersService",
]
