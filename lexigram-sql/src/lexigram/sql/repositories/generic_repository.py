"""Simple Generic RepositoryProtocol implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.di.decorators import inject
from lexigram.sql.exceptions import RepositoryError
from lexigram.sql.repositories.base import SQLRepository
from lexigram.sql.repositories.filter_objects import Filter

if TYPE_CHECKING:
    from lexigram.sql.row_level_security import RowLevelSecurityPolicy

TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey")


@inject
class GenericRepository(SQLRepository[TEntity, TKey], Generic[TEntity, TKey]):
    """
    Generic repository with type safety.

    Provides strongly-typed CRUD operations for entities.
    """

    def __init__(
        self,
        provider: DatabaseProviderProtocol,
        table_name: str,
        entity_class: type[TEntity],
        key_field: str = "id",
        soft_delete_enabled: bool = False,
        multi_tenant: bool | None = None,
        rls_policy: RowLevelSecurityPolicy | None = None,
    ):
        if multi_tenant is None:
            multi_tenant = getattr(entity_class, "is_multi_tenant", False)

        super().__init__(
            provider,
            table_name,
            key_field,
            soft_delete_enabled,
            multi_tenant=multi_tenant,
            rls_policy=rls_policy,
        )
        self.entity_class = entity_class

    def _entity_to_dict(self, entity: TEntity) -> dict[str, Any]:
        """Convert entity to dictionary."""
        from lexigram.domain import DomainModel

        if isinstance(entity, DomainModel):
            # DomainModel (dataclass-based)
            return cast("dict[str, Any]", entity.model_dump())
        if hasattr(entity, "__dict__"):
            return entity.__dict__.copy()
        if isinstance(entity, dict):
            return entity.copy()
        raise RepositoryError(
            f"Cannot convert entity of type {type(entity)} to dict",
        )

    def _row_to_entity(self, row: dict[str, Any]) -> TEntity:
        """Convert database row to entity."""
        from lexigram.domain import DomainModel

        if self.entity_class is dict:
            return cast("TEntity", row)

        # Entity mapping and validation
        if issubclass(self.entity_class, DomainModel):
            # DomainModel (dataclass-based)
            return cast("TEntity", self.entity_class.model_validate(row))
        # Regular class constructor
        return self.entity_class(**row)

    # ------------------------------------------------------------------
    # Convenience aliases
    # ------------------------------------------------------------------

    async def find(
        self,
        filters: dict[str, Any]
        | Filter
        | list[Filter]
        | tuple[Filter, ...]
        | None = None,
        limit: int | None = None,
        offset: int | None = 0,
        sort_by: str | None = None,
        sort_order: str = "asc",
        columns: list[str] | None = None,
        include_deleted: bool = False,
    ) -> list[TEntity]:
        """Find entities with optional dict-style filters.

        Convenience wrapper around ``find_many()`` that accepts ``filters``
        as a plain dict instead of ``**kwargs``.
        """
        typed_filters: tuple[Filter, ...] = ()
        keyword_filters: dict[str, Any] = {}

        if isinstance(filters, Filter):
            typed_filters = (filters,)
        elif isinstance(filters, (list, tuple)):
            typed_filters = tuple(filters)
        elif filters is not None:
            keyword_filters = filters

        return await self.find_many(
            *typed_filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            columns=columns,
            include_deleted=include_deleted,
            **keyword_filters,
        )

    async def get(self, key: TKey) -> TEntity | None:  # type: ignore[override]
        """Get a single entity by primary key.

        Convenience alias for ``find_by_id()``.
        """
        return await self.find_by_id(key)
