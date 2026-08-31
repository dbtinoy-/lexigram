"""Tests for the DeleteActionHandler can_delete guard.

Verifies that resource-level ``can_delete`` is honored by the delete
route: protected records are left untouched and the caller gets an error
signal, while deletable records pass through to the data source.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from starlette.requests import Request

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.action_handlers import DeleteActionHandler


class _ProtectedResource(Resource):
    """Generic resource that refuses to delete records named 'locked'."""

    name = "items"

    def can_delete(self, item: Any) -> bool:
        """Block deletion of records flagged as protected."""
        return not (isinstance(item, dict) and item.get("protected"))


class _AsyncProtectedResource(_ProtectedResource):
    """Resource whose record guard is asynchronous."""

    async def can_delete(self, item: Any) -> bool:
        return await _AsyncProtectedResource._allow(item)

    @staticmethod
    async def _allow(item: Any) -> bool:
        return not (isinstance(item, dict) and item.get("protected"))


class TestDeleteActionHandlerGuard:
    """HTTP-surface tests for the can_delete guard in delete."""

    def setup_method(self) -> None:
        self.handler = DeleteActionHandler()
        self.resource = _ProtectedResource()
        self.resource._data_source = _FakeDataSource()

    def _make_request(
        self, *, method: str = "POST", htmx: bool = False, item_id: str = "1"
    ) -> Request:
        headers = [(b"hx-request", b"true")] if htmx else []
        scope: dict[str, Any] = {
            "type": "http",
            "method": method,
            "path": f"/admin/items/{item_id}/delete",
            "query_string": b"",
            "headers": headers,
            "path_params": {"id": item_id},
            "app": None,
            "state": MagicMock(),
            "admin_resource_prefix": "items",
        }
        return Request(scope)

    async def test_delete_protected_record_is_blocked(self) -> None:
        """can_delete False surfaces an error and never reaches the store."""
        request = self._make_request(item_id="1")
        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 409
        assert self.resource._data_source.deleted == []

    async def test_delete_protected_record_htmx_toasts_without_redirect(
        self,
    ) -> None:
        """HTMX deletes return an error toast instead of a redirect."""
        request = self._make_request(item_id="1", htmx=True)
        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 200
        assert "HX-Trigger" in response.headers
        assert "cannot be deleted" in response.headers["HX-Trigger"]
        assert "HX-Redirect" not in response.headers
        assert self.resource._data_source.deleted == []

    async def test_async_delete_guard_is_awaited(self) -> None:
        resource = _AsyncProtectedResource()
        resource._data_source = _FakeDataSource()
        request = self._make_request(item_id="1")

        response = await self.handler.handle(request, resource)

        assert response.status_code == 409
        assert resource._data_source.deleted == []

    async def test_delete_missing_record_is_not_found(self) -> None:
        """Unknown ids return 404 without touching the store."""
        request = self._make_request(item_id="404")
        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 404
        assert self.resource._data_source.deleted == []

    async def test_delete_allowed_record_reaches_store(self) -> None:
        """can_delete True performs the delete as before."""
        request = self._make_request(item_id="2")
        response = await self.handler.handle(request, self.resource)

        assert response.status_code == 200
        assert self.resource._data_source.deleted == ["2"]


class _FakeDataSource:
    """In-memory data source with two records (one protected)."""

    def __init__(self) -> None:
        self.records = {
            "1": {"id": "1", "name": "locked", "protected": True},
            "2": {"id": "2", "name": "free"},
        }
        self.deleted: list[str] = []

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        """Fetch a record by id."""
        return self.records.get(str(item_id))

    async def delete(self, item_id: Any) -> bool:
        """Delete a record by id."""
        key = str(item_id)
        if key not in self.records:
            return False
        self.deleted.append(key)
        del self.records[key]
        return True
