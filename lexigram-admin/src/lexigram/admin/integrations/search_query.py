from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from lexigram.admin.data.data_source import QueryResult
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.data.query import QuerySpec

_log = get_logger(__name__)


class SearchQueryDataSourceWrapper:
    """Wraps an IDataSource to route within-resource search through FTS.

    Intercepts ``find_many()`` and ``count()`` when the ``QuerySpec`` has
    an active search term.  Instead of passing ``search``/``search_fields``
    through to the inner data source (which would generate ILIKE), it
    queries the search engine for matching document IDs and adds an
    ``id__in`` filter.

    Errors from the search engine are logged at DEBUG level and the query
    falls through without search filtering (no FTS, no ILIKE).
    """

    def __init__(self, inner: Any, search_engine: Any, index_name: str, fallback_to_like: bool = True) -> None:
        self._inner = inner
        self._search_engine = search_engine
        self._index_name = index_name
        self._fallback_to_like = fallback_to_like

    async def find_one(self, item_id: Any) -> Any | None:
        return await self._inner.find_one(item_id)

    async def find_many(self, query: QuerySpec) -> QueryResult:
        if not query.has_search:
            return await self._inner.find_many(query)

        try:
            matched_ids, total = await self._fetch_matching_ids(query)
            _log.info(
                "search.query_wrapper_engine_result",
                index=self._index_name,
                search=query.search,
                matched_ids=len(matched_ids) if matched_ids else 0,
                total=total,
                fallback_to_like=self._fallback_to_like,
            )
            if matched_ids is None:
                _log.info("search.query_wrapper_engine_error", index=self._index_name)
                cleared = replace(query, search=None, search_fields=[])
                return await self._inner.find_many(cleared)
            if not matched_ids:
                if self._fallback_to_like:
                    return await self._inner.find_many(query)
                return QueryResult(items=[], total=0)
            page_size = max(query.per_page, 1)
            page_offset = max(query.page, 1) - 1
            page_ids = matched_ids[page_offset * page_size: (page_offset + 1) * page_size]
            filtered = replace(query, search=None, search_fields=[])
            if page_ids:
                filtered = filtered.with_filters(id__in=page_ids)
            return await self._inner.find_many(filtered)
        except Exception:
            _log.info(
                "search.query_wrapper_error",
                index=self._index_name,
                exc_info=True,
            )
            cleared = replace(query, search=None, search_fields=[])
            return await self._inner.find_many(cleared)

    async def count(self, query: QuerySpec) -> int:
        if not query.has_search:
            return await self._inner.count(query)
        try:
            _, total = await self._fetch_matching_ids(query)
            return total
        except Exception:
            _log.debug(
                "search.count_wrapper_error",
                index=self._index_name,
                exc_info=True,
            )
            cleared = replace(query, search=None, search_fields=[])
            return await self._inner.count(cleared)

    async def create(self, data: dict[str, Any]) -> Any:
        return await self._inner.create(data)

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        return await self._inner.update(item_id, data)

    async def delete(self, item_id: Any) -> bool:
        return await self._inner.delete(item_id)

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[Any]:
        return await self._inner.bulk_create(items)

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        return await self._inner.bulk_update(ids, data)

    async def bulk_delete(self, ids: list[Any]) -> int:
        return await self._inner.bulk_delete(ids)

    async def _fetch_matching_ids(
        self, query: QuerySpec
    ) -> tuple[list[str] | None, int]:
        """Query the search engine and return (ids_for_page, total_count)."""
        page = max(query.page, 1)
        per_page = max(query.per_page, 1)
        offset = (page - 1) * per_page
        limit = per_page

        result = await self._search_engine.search(
            index_name=self._index_name,
            query=query.search,
            limit=limit,
            offset=offset,
        )

        if hasattr(result, "is_ok"):
            if not result.is_ok():
                return (None, 0)
            response = result.unwrap()
        else:
            response = result

        total = response.total if hasattr(response, "total") else 0
        results_list = (
            response.results if hasattr(response, "results") else (response or [])
        )

        ids = []
        for r in results_list:
            rid = r.id if hasattr(r, "id") else (r.get("id") if isinstance(r, dict) else None)
            if rid is not None:
                ids.append(str(rid))

        return (ids, total)


def _empty_result(query: QuerySpec) -> QueryResult:
    from lexigram.admin.data.data_source import QueryResult

    return QueryResult(
        items=[],
        total=0,
        page=query.page,
        per_page=query.per_page,
    )


__all__ = ["SearchQueryDataSourceWrapper"]
