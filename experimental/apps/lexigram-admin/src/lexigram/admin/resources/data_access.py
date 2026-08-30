"""Small data-source resolution helpers shared by resource render/mutation paths."""

from __future__ import annotations

import inspect
from typing import Any


async def _maybe_await(value: Any) -> Any:
    """Return an async result or a synchronous legacy-service result."""
    return await value if inspect.isawaitable(value) else value


class _LegacyServiceDataSource:
    """Adapt the pre-``IDataSource`` service API to resource data access.

    Older resources commonly expose ``service.list()``, ``get_by_id()``, and
    CRUD methods directly, while the current admin pipeline speaks in terms of
    ``find_many``/``find_one``. Keeping this adapter at the resolution
    boundary makes list, detail, forms, relation options, and mutations use
    one operational path instead of silently rendering empty placeholders.
    """

    _is_legacy_service_adapter = True

    def __init__(self, service: Any) -> None:
        self._service = service

    async def find_one(self, item_id: Any) -> Any:
        getter = getattr(self._service, "find_one", None)
        if getter is None:
            getter = getattr(self._service, "get_by_id", None)
        if getter is None:
            getter = getattr(self._service, "get", None)
        if getter is None:
            return None
        return await _maybe_await(getter(item_id))

    async def find_many(self, query: Any) -> Any:
        from lexigram.admin.data.data_source import QueryResult

        finder = getattr(self._service, "find_many", None)
        if finder is not None:
            result = await _maybe_await(finder(query))
            if hasattr(result, "items"):
                return result
            return QueryResult(
                items=list(result or []),
                total=len(result or []),
                page=getattr(query, "page", 1),
                per_page=getattr(query, "per_page", 20),
            )

        lister = getattr(self._service, "list", None)
        if lister is None:
            return QueryResult(items=[], total=0)
        try:
            result = await _maybe_await(
                lister(
                    limit=getattr(query, "per_page", 20),
                    offset=(getattr(query, "page", 1) - 1)
                    * getattr(query, "per_page", 20),
                )
            )
        except TypeError:
            # A number of legacy services only expose ``list()``.
            result = await _maybe_await(lister())
        if hasattr(result, "items"):
            return result
        items = list(result or [])
        return QueryResult(
            items=items,
            total=len(items),
            page=getattr(query, "page", 1),
            per_page=getattr(query, "per_page", 20),
            has_next=False,
            has_prev=getattr(query, "page", 1) > 1,
        )

    async def count(self, query: Any) -> int:
        counter = getattr(self._service, "count", None)
        if counter is not None:
            try:
                return int(await _maybe_await(counter(query)))
            except TypeError:
                return int(await _maybe_await(counter()))
        result = await self.find_many(query)
        return int(getattr(result, "total", len(getattr(result, "items", []))))

    async def create(self, data: dict[str, Any]) -> Any:
        creator = getattr(self._service, "create", None)
        if creator is None:
            raise NotImplementedError("Legacy service does not support create")
        return await _maybe_await(creator(data))

    async def update(self, item_id: Any, data: dict[str, Any]) -> Any:
        updater = getattr(self._service, "update", None)
        if updater is None:
            raise NotImplementedError("Legacy service does not support update")
        try:
            return await _maybe_await(updater(item_id, data))
        except TypeError:
            return await _maybe_await(updater(data, item_id))

    async def delete(self, item_id: Any) -> bool:
        deleter = getattr(self._service, "delete", None)
        if deleter is None:
            raise NotImplementedError("Legacy service does not support delete")
        return bool(await _maybe_await(deleter(item_id)))

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[Any]:
        creator = getattr(self._service, "bulk_create", None)
        if creator is not None:
            return list(await _maybe_await(creator(items)) or [])
        return [await self.create(item) for item in items]

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        updater = getattr(self._service, "bulk_update", None)
        if updater is not None:
            return int(await _maybe_await(updater(ids, data)))
        count = 0
        for item_id in ids:
            if await self.update(item_id, data) is not None:
                count += 1
        return count

    async def bulk_delete(self, ids: list[Any]) -> int:
        deleter = getattr(self._service, "bulk_delete", None)
        if deleter is not None:
            return int(await _maybe_await(deleter(ids)))
        count = 0
        for item_id in ids:
            if await self.delete(item_id):
                count += 1
        return count


def _adapt_source(source: Any) -> Any | None:
    """Wrap a legacy service unless it already implements the source API."""
    if source is None or getattr(source, "_is_legacy_service_adapter", False):
        return source
    required = ("find_one", "find_many", "create", "update", "delete")
    if all(callable(getattr(source, name, None)) for name in required):
        return source
    if any(
        callable(getattr(source, name, None))
        for name in ("list", "get", "get_by_id", "find_many")
    ):
        return _LegacyServiceDataSource(source)
    return source


def get_resource_data_source(resource: Any) -> Any | None:
    """Resolve a resource's wired or lazily-provided data source.

    Mounted resources normally store their source on ``_data_source``. Custom
    resources may expose a ``get_data_source()`` method instead, and legacy
    resources may expose a service with ``list``/``get_by_id`` methods. All
    forms of resource access are normalized here so CRUD, relation options,
    and detail rendering do not silently fall back to non-operational output.
    """
    if resource is None:
        return None

    source = getattr(resource, "_data_source", None)
    if source is None:
        getter = getattr(resource, "get_data_source", None)
        if callable(getter):
            try:
                source = getter()
            except (
                AttributeError,
                NotImplementedError,
                RuntimeError,
                TypeError,
                ValueError,
            ):
                source = None
    if source is None:
        source = getattr(resource, "data_source", None)
    if source is None:
        # Backward-compatible resource declarations (notably UserResource)
        # attach their service directly rather than calling set_data_source.
        source = getattr(resource, "service", None)

    return _adapt_source(source)


__all__ = ["get_resource_data_source"]
