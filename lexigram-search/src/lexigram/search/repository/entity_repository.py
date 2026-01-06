"""Search-engine-backed repository extending the platform AbstractRepository.

Provides a ``SearchEntityRepository`` that bridges the platform's standard
``AbstractRepository[T, str]`` interface with a search engine backend, enabling
search-backed repositories to satisfy the ``RepositoryProtocol`` protocol and be used
interchangeably with database-backed repositories.
"""

from __future__ import annotations

import abc
from typing import Any, Generic, TypeVar

from lexigram.contracts.domain.specification import SpecificationProtocol
from lexigram.contracts.exceptions.domain import NotFoundError
from lexigram.primitives.data import AbstractRepository
from lexigram.result import Err, Ok, Result
from lexigram.search.engine import SearchEngine, SearchQuery
from lexigram.search.exceptions import SearchError

__all__ = ["SearchEntityRepository"]

T = TypeVar("T")


class SearchEntityRepository(AbstractRepository[T, str], Generic[T]):
    """Search-engine-backed repository implementing the platform RepositoryProtocol protocol.

    Extends :class:`AbstractRepository` with search-specific query capabilities,
    enabling search-backed repositories to satisfy the same ``RepositoryProtocol[T]``
    protocol as database-backed repositories (Liskov Substitution Principle).

    Subclasses must implement :meth:`_to_document` and :meth:`_from_document`
    to define entity ↔ search-document serialization, and may override
    :meth:`_get_document_id` if the entity ID is not stored in the ``"id"``
    field of the document.

    Example::

        class ProductRepository(SearchEntityRepository[Product]):
            def _to_document(self, entity: Product) -> dict[str, Any]:
                return {"id": entity.id, "name": entity.name, "price": entity.price}

            def _from_document(self, doc: dict[str, Any]) -> Product:
                return Product(**doc)

    Args:
        engine: The search engine backend to delegate operations to.
        index_name: The name of the search index that stores entities of type ``T``.
    """

    def __init__(
        self,
        engine: SearchEngine,
        index_name: str,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._index_name = index_name

    # ------------------------------------------------------------------
    # Serialization primitives — must be implemented by concrete subclasses
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def _to_document(self, entity: T) -> dict[str, Any]:
        """Serialize an entity to a search document dict.

        Args:
            entity: The entity to serialize.

        Returns:
            A dict representation suitable for indexing.
        """

    @abc.abstractmethod
    def _from_document(self, document: dict[str, Any]) -> T:
        """Deserialize a search document dict into an entity.

        Args:
            document: The raw document dict from the search engine.

        Returns:
            The deserialized entity.
        """

    def _get_document_id(self, entity: T) -> str:
        """Extract the document ID from an entity.

        Override this if the ID field is not named ``"id"`` on the entity.

        Args:
            entity: The entity from which to extract the ID.

        Returns:
            The string document ID.
        """
        return str(entity.id)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # AbstractReadOnlyRepository primitives
    # ------------------------------------------------------------------

    async def _fetch_by_id(self, entity_id: Any) -> T | None:
        """Retrieve a document from the search index by its ID.

        Args:
            entity_id: The string document ID to look up.

        Returns:
            The deserialized entity, or ``None`` if not found.
        """
        doc = await self._engine.get_document(self._index_name, str(entity_id))  # type: ignore[attr-defined]
        if doc is None:
            return None
        return self._from_document(doc)

    async def _fetch_many(
        self,
        *,
        skip: int,
        limit: int,
        filters: dict[str, Any],
    ) -> list[T]:
        """Retrieve a filtered, paginated list of entities via search.

        Args:
            skip: Number of results to skip.
            limit: Maximum number of results to return.
            filters: Attribute equality filters translated to search filters.

        Returns:
            Matching deserialized entities.
        """
        query = SearchQuery(
            q="*",
            filters=filters or None,
            limit=limit,
            offset=skip,
        )
        result = await self._engine.search(self._index_name, query)  # type: ignore[arg-type]
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()
        hits: list[dict[str, Any]] = (
            response.get("hits", []) if isinstance(response, dict) else []
        )
        return [self._from_document(hit) for hit in hits]

    async def _count(self, *, filters: dict[str, Any]) -> int:
        """Count entities matching the given filters.

        Args:
            filters: Attribute equality filters.

        Returns:
            Total count of matching entities.
        """
        query = SearchQuery(
            q="*",
            filters=filters or None,
            limit=0,
            offset=0,
        )
        result = await self._engine.search(self._index_name, query)  # type: ignore[arg-type]
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()
        if isinstance(response, dict):
            return int(response.get("total", 0))
        return 0

    async def find_by_spec(
        self,
        spec: SpecificationProtocol[T],
    ) -> list[T]:
        """Return all entities that satisfy the given specification.

        Fetches all documents via a wildcard query and applies the specification
        in-memory. For large indices, prefer overriding this method to push
        filter logic into the search engine.

        Args:
            spec: A ``SpecificationProtocol`` whose ``is_satisfied_by`` predicate is
                applied to each retrieved entity.

        Returns:
            All entities satisfying the specification.
        """
        all_entities = await self._fetch_many(skip=0, limit=10_000, filters={})
        return [e for e in all_entities if spec.is_satisfied_by(e)]

    # ------------------------------------------------------------------
    # AbstractRepository write primitives
    # ------------------------------------------------------------------

    async def _save(self, entity: T) -> T:
        """Index (insert or update) an entity in the search backend.

        Args:
            entity: The entity to persist.

        Returns:
            The entity unchanged (search backends do not modify entities on save).
        """
        doc_id = self._get_document_id(entity)
        document = self._to_document(entity)
        await self._engine.index_document(self._index_name, doc_id, document)  # type: ignore[attr-defined]
        return entity

    async def save_many(self, entities: list[T]) -> list[T]:
        """Index a batch of entities using a single bulk operation.

        Prefer this over calling :meth:`save` in a loop when persisting
        multiple entities at once. Uses :meth:`SearchEngine.index_many` to
        issue a single bulk request, avoiding N separate index round-trips.

        Args:
            entities: The list of entities to index.

        Returns:
            The same list of entities unchanged.
        """
        if not entities:
            return entities
        documents = [
            (self._get_document_id(entity), self._to_document(entity))
            for entity in entities
        ]
        await self._engine.index_many(self._index_name, documents)  # type: ignore[attr-defined]
        return entities

    async def _delete(self, entity_id: Any) -> bool:
        """Remove the entity with the given ID from the search index.

        Args:
            entity_id: The ID of the entity to remove.

        Returns:
            ``True`` if deleted, ``False`` if it did not exist.
        """
        return await self._engine.delete_document(self._index_name, str(entity_id))  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Search-specific extension
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        fields: list[str] | None = None,
    ) -> Result[list[T], SearchError]:
        """Execute a full-text search query against the index.

        This is a search-specific extension on top of the base repository
        interface. Use this for user-facing search features rather than
        ``list()`` / ``find_by_spec()``.

        Args:
            query: The full-text query string.
            filters: Optional attribute equality filters to narrow results.
            limit: Maximum number of results to return.
            offset: Number of results to skip.
            fields: Optional list of fields to return; defaults to all fields.

        Returns:
            ``Ok(list[T])`` on success, ``Err(SearchError)`` on backend failure.
        """
        search_query = SearchQuery(
            q=query,
            filters=filters,
            limit=limit,
            offset=offset,
            fields=fields,
        )
        result = await self._engine.search(self._index_name, search_query)  # type: ignore[arg-type]
        if result.is_err():
            return Err(result.unwrap_err())
        response = result.unwrap()
        hits: list[dict[str, Any]] = (
            response.get("hits", []) if isinstance(response, dict) else []
        )
        return Ok([self._from_document(hit) for hit in hits])

    async def find(self, entity_id: str) -> Result[T, NotFoundError]:
        """Retrieve an entity by ID, returning a typed ``Result``.

        Provides an explicit ``Result``-typed alternative to ``get()`` for
        callers that prefer structured error handling over ``None`` checks.

        Args:
            entity_id: The string ID of the entity to look up.

        Returns:
            ``Ok(entity)`` if found, ``Err(NotFoundError)`` otherwise.
        """
        entity = await self._fetch_by_id(entity_id)
        if entity is None:
            return Err(
                NotFoundError(
                    f"Entity with id={entity_id!r} not found in index"
                    f" {self._index_name!r}"
                )
            )
        return Ok(entity)
