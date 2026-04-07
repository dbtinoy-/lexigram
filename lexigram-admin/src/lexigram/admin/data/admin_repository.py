"""In-memory repository implementation for AdminUserAggregate.

Provides a concrete ``AbstractRepository`` implementation backed by an
in-memory dict, suitable for testing and lightweight scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.domain.aggregate import AdminUserAggregate
from lexigram.primitives.data import AbstractRepository

if TYPE_CHECKING:
    from lexigram.contracts.domain.specification import SpecificationProtocol


class AdminUserRepository(AbstractRepository[AdminUserAggregate, str]):
    """In-memory repository for AdminUserAggregate instances.

    Stores aggregates in a plain dict keyed by their ``id``.  Intended for
    use in tests and as a reference implementation; production deployments
    should supply a database-backed subclass.
    """

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[str, AdminUserAggregate] = {}

    # ------------------------------------------------------------------
    # Read primitives
    # ------------------------------------------------------------------

    async def _fetch_by_id(self, entity_id: Any) -> AdminUserAggregate | None:
        return self._store.get(str(entity_id))

    async def _fetch_many(
        self,
        *,
        skip: int,
        limit: int,
        filters: dict[str, Any],
    ) -> list[AdminUserAggregate]:
        items = list(self._store.values())
        for field_name, value in filters.items():
            items = [i for i in items if getattr(i, field_name, None) == value]
        return items[skip : skip + limit]

    async def _count(self, *, filters: dict[str, Any]) -> int:
        items = list(self._store.values())
        for field_name, value in filters.items():
            items = [i for i in items if getattr(i, field_name, None) == value]
        return len(items)

    async def find_by_spec(
        self,
        spec: SpecificationProtocol[AdminUserAggregate],
    ) -> list[AdminUserAggregate]:
        """Return all aggregates that satisfy *spec*."""
        return [item for item in self._store.values() if spec.is_satisfied_by(item)]

    # ------------------------------------------------------------------
    # Write primitives
    # ------------------------------------------------------------------

    async def _save(self, entity: AdminUserAggregate) -> AdminUserAggregate:
        self._store[str(entity.id)] = entity
        return entity

    async def _delete(self, entity_id: Any) -> bool:
        key = str(entity_id)
        if key not in self._store:
            return False
        del self._store[key]
        return True
