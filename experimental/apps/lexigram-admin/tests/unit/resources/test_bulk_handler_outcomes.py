"""BulkActionHandler per-row outcome tests (R14 — docs/09-01-2026/09-bulk-ux.md)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.handler import BulkActionHandler


class _FakeDataSource:
    """In-memory data source with programmable failure modes."""

    def __init__(self, records: dict[str, dict[str, Any]] | None = None) -> None:
        self._store: dict[str, dict[str, Any]] = records if records is not None else {
            "1": {"id": "1", "name": "one"},
            "2": {"id": "2", "name": "two"},
        }
        self.reject_delete_ids: set[str] = set()
        self.raise_on_delete_ids: set[str] = set()
        self.reject_update_ids: set[str] = set()

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return self._store.get(str(item_id))

    async def delete(self, item_id: Any) -> bool:
        key = str(item_id)
        if key in self.raise_on_delete_ids:
            raise RuntimeError("storage exploded")
        if key in self.reject_delete_ids:
            return False
        return self._store.pop(key, None) is not None

    async def update(
        self, item_id: Any, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        key = str(item_id)
        if key in self.reject_update_ids:
            return None
        record = self._store.get(key)
        if record is None:
            return None
        record.update(data)
        return record


class _Items(Resource):
    name = "items"


def _resource(ds: _FakeDataSource) -> _Items:
    resource = _Items()
    resource._data_source = ds
    return resource


def _request(
    form: dict[str, Any],
    *,
    htmx: bool = False,
) -> Request:
    headers = [(b"hx-request", b"true")] if htmx else []
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/admin/items/bulk",
        "query_string": b"",
        "headers": headers,
        "path_params": {},
        "app": None,
        "state": MagicMock(),
        "admin_resource_prefix": "items",
    }
    request = Request(scope)
    form_obj = MagicMock()
    form_obj.get = lambda key, default=None: form.get(key, default)
    form_obj.getlist = lambda key: form.get(f"{key}__list", [])
    request.scope["admin_form_data"] = form_obj
    return request


def _toast(response: Any) -> dict[str, Any]:
    return json.loads(response.headers["HX-Trigger"])["show-toast"]


class TestBulkDeleteOutcomes:
    @pytest.mark.asyncio
    async def test_missing_rows_reported_not_silently_skipped(self) -> None:
        ds = _FakeDataSource()
        outcome = await BulkActionHandler._bulk_delete(
            _resource(ds), ds, ["1", "missing"], purge=False
        )
        assert outcome.succeeded == 1
        assert outcome.failures == [("missing", "not found")]

    @pytest.mark.asyncio
    async def test_storage_rejection_reported(self) -> None:
        ds = _FakeDataSource()
        ds.reject_delete_ids = {"2"}
        outcome = await BulkActionHandler._bulk_delete(
            _resource(ds), ds, ["1", "2"], purge=False
        )
        assert outcome.succeeded == 1
        assert outcome.failures == [("2", "rejected by storage")]

    @pytest.mark.asyncio
    async def test_one_raising_row_does_not_abort_the_batch(self) -> None:
        ds = _FakeDataSource(
            {"1": {"id": "1"}, "2": {"id": "2"}, "3": {"id": "3"}}
        )
        ds.raise_on_delete_ids = {"2"}
        outcome = await BulkActionHandler._bulk_delete(
            _resource(ds), ds, ["1", "2", "3"], purge=False
        )
        assert outcome.succeeded == 2
        assert outcome.failures == [("2", "error")]
        assert "1" not in ds._store and "3" not in ds._store

    @pytest.mark.asyncio
    async def test_permission_error_is_per_row_forbidden(self) -> None:
        ds = _FakeDataSource()
        resource = _resource(ds)

        async def before_delete(item_id: str) -> None:
            if item_id == "2":
                raise PermissionError("nope")

        resource.before_delete = before_delete  # type: ignore[method-assign]
        outcome = await BulkActionHandler._bulk_delete(
            resource, ds, ["1", "2"], purge=False
        )
        assert outcome.succeeded == 1
        assert outcome.failures == [("2", "forbidden")]

    @pytest.mark.asyncio
    async def test_soft_delete_rejection_reported(self) -> None:
        ds = _FakeDataSource()
        ds.reject_update_ids = {"2"}
        resource = _resource(ds)
        resource.soft_delete_enabled = True  # type: ignore[attr-defined]
        outcome = await BulkActionHandler._bulk_delete(
            resource, ds, ["1", "2"], purge=False
        )
        assert outcome.succeeded == 1
        assert outcome.failures == [("2", "rejected by storage")]
        assert "deleted_at" in ds._store["1"]


class TestBulkPurgeOutcomes:
    @pytest.mark.asyncio
    async def test_purge_lookup_error_reported_per_row(self) -> None:
        ds = _FakeDataSource()
        outcome = await BulkActionHandler._bulk_delete(
            _resource(ds), ds, ["1", "missing"], purge=True
        )
        assert outcome.succeeded == 1
        assert outcome.failures == [("missing", "not found")]

    @pytest.mark.asyncio
    async def test_purge_without_callable_hook_raises_not_implemented(self) -> None:
        # Pre-R14 this silently no-opped and reported "Purged 0 item(s)"
        # with a success toast.
        ds = _FakeDataSource()
        resource = _resource(ds)
        resource.purge = None  # type: ignore[assignment]
        with pytest.raises(NotImplementedError):
            await BulkActionHandler._bulk_delete(
                resource, ds, ["1"], purge=True
            )

    @pytest.mark.asyncio
    async def test_purge_unavailable_maps_to_503_via_handle(self) -> None:
        ds = _FakeDataSource()
        resource = _resource(ds)
        resource.purge = None  # type: ignore[assignment]
        request = _request({"action": "purge", "ids__list": ["1"]})
        response = await BulkActionHandler().handle(request, resource)
        assert response.status_code == 503
        assert b"Purge is unavailable" in response.body


class TestBulkRestoreOutcomes:
    @pytest.mark.asyncio
    async def test_restore_hook_none_result_reported(self) -> None:
        ds = _FakeDataSource()
        resource = _resource(ds)

        async def restore(item_id: str) -> Any:
            return {"id": item_id} if item_id == "1" else None

        resource.restore = restore  # type: ignore[method-assign]
        outcome = await BulkActionHandler._bulk_restore(resource, ds, ["1", "2"])
        assert outcome.succeeded == 1
        assert outcome.failures == [("2", "restore rejected")]

    @pytest.mark.asyncio
    async def test_restore_hook_lookup_error_reported(self) -> None:
        ds = _FakeDataSource()
        resource = _resource(ds)

        async def restore(item_id: str) -> Any:
            if item_id == "2":
                raise LookupError("gone")
            return {"id": item_id}

        resource.restore = restore  # type: ignore[method-assign]
        outcome = await BulkActionHandler._bulk_restore(resource, ds, ["1", "2"])
        assert outcome.succeeded == 1
        assert outcome.failures == [("2", "not found")]

    @pytest.mark.asyncio
    async def test_restore_update_fallback_missing_row_reported(self) -> None:
        ds = _FakeDataSource()
        resource = _resource(ds)
        resource.restore = None  # type: ignore[assignment]
        outcome = await BulkActionHandler._bulk_restore(
            resource, ds, ["1", "missing"]
        )
        assert outcome.succeeded == 1
        assert outcome.failures == [("missing", "not found")]
        assert ds._store["1"]["deleted_at"] is None


class TestHandleToasts:
    @pytest.mark.asyncio
    async def test_all_success_toast_unchanged(self) -> None:
        ds = _FakeDataSource()
        request = _request(
            {"action": "delete", "ids__list": ["1", "2"]}, htmx=True
        )
        response = await BulkActionHandler().handle(request, _resource(ds))
        assert response.status_code == 200
        toast = _toast(response)
        assert toast["message"] == "Deleted 2 item(s)"
        assert toast["type"] == "success"
        assert "duration" not in toast

    @pytest.mark.asyncio
    async def test_partial_failure_toast_is_warning_with_duration(self) -> None:
        ds = _FakeDataSource()
        request = _request(
            {"action": "delete", "ids__list": ["1", "missing"]}, htmx=True
        )
        response = await BulkActionHandler().handle(request, _resource(ds))
        assert response.status_code == 200
        toast = _toast(response)
        assert toast["type"] == "warning"
        assert toast["duration"] == 8000
        assert "Deleted 1 of 2 item(s)" in toast["message"]
        assert "missing (not found)" in toast["message"]
        # refresh-list still fires so completed work is reflected.
        assert json.loads(response.headers["HX-Trigger"])["refresh-list"] is True

    @pytest.mark.asyncio
    async def test_total_failure_toast_is_error(self) -> None:
        ds = _FakeDataSource()
        request = _request(
            {"action": "delete", "ids__list": ["nope1", "nope2"]}, htmx=True
        )
        response = await BulkActionHandler().handle(request, _resource(ds))
        toast = _toast(response)
        assert toast["type"] == "error"
        assert "Deleted 0 of 2 item(s)" in toast["message"]

    @pytest.mark.asyncio
    async def test_non_htmx_still_redirects(self) -> None:
        ds = _FakeDataSource()
        request = _request({"action": "delete", "ids__list": ["1", "missing"]})
        response = await BulkActionHandler().handle(request, _resource(ds))
        assert response.status_code == 302
