"""Unified data source interfaces for Lexigram Admin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from lexigram.admin.data.query import QuerySpec

# Type variable for the entity type
T = TypeVar("T")


@dataclass
class QueryResult(Generic[T]):
    """Result of a data query with pagination and metadata.

    Attributes:
        items: The list of entities returned by the query.
        total: Total number of entities matching the query (for pagination).
        page: Current page number (1-indexed).
        per_page: Number of items per page.
        has_next: Whether there is a next page.
        has_prev: Whether there is a previous page.
        cursor: Optional cursor for cursor-based pagination.
    """

    items: list[T]
    total: int = 0
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_prev: bool = False
    cursor: str | None = None


@runtime_checkable
class IDataSource(Protocol[T]):
    """Protocol for unified data access.

    .. stability:: stable

    This interface abstracts away the underlying data storage (DB, API, etc.)
    providing a consistent API for the Admin UI and Resource Managers.
    """

    async def find_one(self, item_id: Any) -> T | None:
        """Find a single entity by its unique identifier.

        Args:
            item_id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        ...

    async def find_many(self, query: QuerySpec) -> QueryResult[T]:
        """Find multiple entities matching the given query specification.

        Args:
            query: The query specification (typically a QuerySpec).

        Returns:
            A QueryResult containing the requested entities and metadata.
        """
        ...

    async def count(self, query: QuerySpec) -> int:
        """Count the total number of entities matching the given query.

        Args:
            query: The query specification.

        Returns:
            The total count of matching entities.
        """
        ...

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new entity with the provided data.

        Args:
            data: Dictionary of entity attributes.

        Returns:
            The created entity.
        """
        ...

    async def update(self, item_id: Any, data: dict[str, Any]) -> T:
        """Update an existing entity.

        Args:
            item_id: The unique identifier of the entity to update.
            data: Dictionary of attributes to update.

        Returns:
            The updated entity.
        """
        ...

    async def delete(self, item_id: Any) -> bool:
        """Delete an entity by its unique identifier.

        Args:
            item_id: The unique identifier of the entity.

        Returns:
            True if deleted successfully, False otherwise.
        """
        ...

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[T]:
        """Create multiple entities in a single operation.

        Args:
            items: List of dictionaries containing entity data.

        Returns:
            List of created entities.
        """
        ...

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        """Update multiple entities matching the provided IDs with the same data.

        Args:
            ids: List of entity identifiers.
            data: Dictionary of attributes to update across all entities.

        Returns:
            The count of updated entities.
        """
        ...

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Delete multiple entities by their identifiers.

        Args:
            ids: List of entity identifiers.

        Returns:
            The count of deleted entities.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete base classes (moved from interfaces/data_source.py)
# ---------------------------------------------------------------------------

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts import (
        DatabaseProviderProtocol,
    )


def _quote_identifier(name: str) -> str:
    """Quote SQL identifier to prevent injection.

    Simple identifier validation - allows alphanumeric and underscore only.
    """
    if not name or not name.replace("_", "").isalnum():
        raise ValueError(f"Invalid SQL identifier: {name}")
    return f'"{name}"'


class DataSourceBase(ABC, Generic[T]):
    """Abstract base class for data sources.

    Provides a consistent interface for CRUD operations
    that can be implemented by different backends (SQL, API, memory, etc.).
    """

    @abstractmethod
    async def find_one(self, item_id: Any) -> T | None:
        """Find a single entity by ID."""
        ...

    @abstractmethod
    async def update(
        self,
        item_id: Any,
        data: dict[str, Any] | None = None,
    ) -> T | None:
        """Update an existing entity."""
        ...

    @abstractmethod
    async def delete(self, item_id: Any) -> bool:
        """Delete an entity by ID."""
        ...

    @abstractmethod
    async def find_many(
        self, query: QuerySpec | None = None, **filters: Any
    ) -> QueryResult[T]:
        """Find multiple entities with optional filtering."""
        ...

    @abstractmethod
    async def create(self, entity: T | dict[str, Any]) -> T:
        """Create a new entity."""
        ...

    async def count(self, query: QuerySpec | None = None) -> int:
        """Count entities matching query."""
        result = await self.find_many(query)
        return result.total


class SqlDataSource(DataSourceBase[T]):
    """SQL-based data source using lexigram-sql.

    Provides a base class for services that need SQL database access.
    Subclasses should implement domain-specific query methods.
    """

    def __init__(
        self,
        db: DatabaseProviderProtocol,
        table_name: str,
        *,
        id_field: str = "id",
    ):
        self.db = db
        self.table_name = table_name
        self.id_field = id_field

    async def find_one(self, item_id: Any) -> T | None:
        """Find a single entity by ID."""
        table = _quote_identifier(self.table_name)
        id_field = _quote_identifier(self.id_field)
        query = f"SELECT * FROM {table} WHERE {id_field} = $1"
        return await self.db.fetch_one(query, [item_id])  # type: ignore[attr-defined]

    async def find_many(
        self,
        query: QuerySpec | None = None,
        *,
        page: int = 1,
        per_page: int = 20,
        **filters: Any,
    ) -> QueryResult[T]:
        """Find multiple entities with pagination."""
        table = _quote_identifier(self.table_name)
        base_query = f"SELECT * FROM {table}"
        count_query = f"SELECT COUNT(*) FROM {table}"

        where_clauses: list[str] = []
        params: list[Any] = []
        for i, (field, value) in enumerate(filters.items(), 1):
            where_clauses.append(f"{_quote_identifier(field)} = ${i}")
            params.append(value)

        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
            base_query += where_sql
            count_query += where_sql

        offset = (page - 1) * per_page
        base_query += f" LIMIT {per_page} OFFSET {offset}"

        items = await self.db.fetch_all(base_query, params)  # type: ignore[attr-defined]
        count_result = await self.db.fetch_one(count_query, params)  # type: ignore[attr-defined]
        total = count_result[0] if count_result else 0

        return QueryResult(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
            has_next=offset + per_page < total,
            has_prev=page > 1,
        )

    async def create(self, entity: T | dict[str, Any]) -> T:
        """Create a new entity."""
        data = (
            entity
            if isinstance(entity, dict)
            else (
                entity.model_dump()
                if hasattr(entity, "model_dump")
                else entity.__dict__
            )
        )
        fields = list(data.keys())
        placeholders = [f"${i}" for i in range(1, len(fields) + 1)]
        values = list(data.values())
        query = f"""
            INSERT INTO {_quote_identifier(self.table_name)} ({", ".join(_quote_identifier(f) for f in fields)})
            VALUES ({", ".join(placeholders)})
            RETURNING *
        """
        return await self.db.fetch_one(query, values)  # type: ignore[attr-defined]

    async def update(
        self,
        item_id: Any,
        data: dict[str, Any] | None = None,
    ) -> T | None:
        """Update an existing entity."""
        if data is None:
            entity = item_id
            data = (
                entity
                if isinstance(entity, dict)
                else (
                    entity.model_dump()
                    if hasattr(entity, "model_dump")
                    else entity.__dict__
                )
            )
            item_id = data.get(self.id_field)
        if not data:
            return None
        update_data = {k: v for k, v in data.items() if k != self.id_field}
        set_clauses = [
            f"{_quote_identifier(field)} = ${i}"
            for i, field in enumerate(update_data.keys(), 1)
        ]
        values = list(update_data.values())
        values.append(item_id)
        query = f"""
            UPDATE {_quote_identifier(self.table_name)}
            SET {", ".join(set_clauses)}
            WHERE {_quote_identifier(self.id_field)} = ${len(values)}
            RETURNING *
        """
        return await self.db.fetch_one(query, values)  # type: ignore[attr-defined]

    async def delete(self, item_id: Any) -> bool:
        """Delete an entity by ID."""
        if hasattr(item_id, self.id_field):
            item_id = getattr(item_id, self.id_field)
        elif isinstance(item_id, dict):
            item_id = item_id.get(self.id_field, item_id)
        table = _quote_identifier(self.table_name)
        id_field = _quote_identifier(self.id_field)
        query = f"DELETE FROM {table} WHERE {id_field} = $1"
        result = await self.db.execute(query, [item_id])
        return result > 0 if isinstance(result, int) else True
