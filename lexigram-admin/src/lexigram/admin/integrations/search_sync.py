from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.data.data_source import QueryResult
    from lexigram.admin.integrations.search import SearchableSpec

_log = get_logger(__name__)


class SearchSyncDataSourceWrapper:
    """Wraps an IDataSource to sync CRUD operations to the search index.

    Intercepts create/update/delete and calls the search engine after
    the underlying data source operation succeeds.  Errors from the
    search engine are logged at DEBUG level and never propagated, so
    a search backend outage does not break admin CRUD.
    """

    def __init__(self, inner: Any, search_engine: Any, spec: SearchableSpec) -> None:
        self._inner = inner
        self._search_engine = search_engine
        self._index_name = spec.index_name
        self._fields = spec.fields

    async def find_one(self, item_id: Any) -> Any | None:
        return await self._inner.find_one(item_id)

    async def find_many(self, query: Any) -> QueryResult:
        return await self._inner.find_many(query)

    async def count(self, query: Any) -> int:
        return await self._inner.count(query)

    async def create(self, data: dict[str, Any]) -> Any:
        entity = await self._inner.create(data)
        await self._index_entity(entity)
        return entity

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        entity = await self._inner.update(item_id, data)
        await self._index_entity(entity)
        return entity

    async def delete(self, item_id: Any) -> bool:
        ok = await self._inner.delete(item_id)
        if ok:
            await self._remove_document(item_id)
        return ok

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[Any]:
        return await self._inner.bulk_create(items)

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        return await self._inner.bulk_update(ids, data)

    async def bulk_delete(self, ids: list[Any]) -> int:
        return await self._inner.bulk_delete(ids)

    async def _index_entity(self, entity: Any) -> None:
        """Upsert *entity* into the search index."""
        doc = self._to_document(entity)
        if doc is None or not self._index_name:
            return
        try:
            result = await self._search_engine.index(self._index_name, [doc])
            if hasattr(result, "is_err") and result.is_err():
                _log.debug("search.index_failed", index=self._index_name)
        except Exception:
            _log.debug("search.index_error", index=self._index_name, exc_info=True)

    async def _remove_document(self, item_id: Any) -> None:
        """Delete the document with *item_id* from the search index."""
        if not self._index_name:
            return
        try:
            result = await self._search_engine.delete(self._index_name, str(item_id))
            if hasattr(result, "is_err") and result.is_err():
                _log.debug("search.delete_failed", index=self._index_name)
        except Exception:
            _log.debug("search.delete_error", index=self._index_name, exc_info=True)

    def _to_document(self, entity: Any) -> dict[str, Any] | None:
        """Build the search document dict from *entity*.

        Handles both ``dict`` and model object entities.  The document
        always includes an ``id`` key extracted from the entity, plus
        the fields declared in ``self._fields``.

        Returns ``None`` when no ID can be extracted.
        """
        if isinstance(entity, dict):
            doc_id = entity.get("id")
            doc = {f: entity.get(f) for f in self._fields}
        else:
            doc_id = getattr(entity, "id", None)
            doc = {f: getattr(entity, f, None) for f in self._fields}
        if doc_id is None:
            return None
        doc["id"] = str(doc_id)
        return doc
