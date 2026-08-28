"""Unit tests for the resource bulk-action execution path."""

from __future__ import annotations

from typing import Any

from lexigram.admin.controllers.resource.bulk import ResourceBulkMixin


class _FakeDataSource:
    """Records calls; find_one returns canned records."""

    def __init__(self, records: dict[str, Any] | None = None) -> None:
        self.records = records or {}
        self.bulk_delete_calls: list[list[str]] = []
        self.update_calls: list[tuple[str, dict[str, Any]]] = []

    async def find_one(self, item_id: str) -> Any:
        return self.records.get(item_id)

    async def bulk_delete(self, ids: list[str]) -> int:
        self.bulk_delete_calls.append(ids)
        return len(ids)

    async def update(self, item_id: str, values: dict[str, Any]) -> Any:
        self.update_calls.append((item_id, values))
        return {"id": item_id, **values}


class _BulkController(ResourceBulkMixin):
    """Minimal host class supplying the mixin's dependencies."""

    def __init__(self, data_source: _FakeDataSource) -> None:
        self._ds = data_source

    def get_data_source(self) -> _FakeDataSource:
        return self._ds

    def _should_dispatch_via_tasks(self, count: int) -> bool:
        return False


class TestExecuteBulkAction:
    async def test_delete_without_can_delete_still_deletes(self) -> None:
        """Backward compatibility: no hook -> bulk delete proceeds."""
        ds = _FakeDataSource({"1": {"id": 1}})
        ctl = _BulkController(ds)
        result = await ctl.execute_bulk_action("delete", ["1"])
        assert result == "Deleted 1 items"
        assert ds.bulk_delete_calls == [["1"]]

    async def test_delete_honors_can_delete_hook(self) -> None:
        ds = _FakeDataSource({"1": {"id": 1}, "2": {"id": 2}})
        ctl = _BulkController(ds)
        ctl.can_delete = lambda item: item["id"] != 2  # type: ignore[attr-defined]
        result = await ctl.execute_bulk_action("delete", ["1", "2"])
        assert result == "Refused: record 2 is protected from deletion"
        assert ds.bulk_delete_calls == []  # nothing deleted

    async def test_delete_allows_when_hook_permits(self) -> None:
        ds = _FakeDataSource({"1": {"id": 1}})
        ctl = _BulkController(ds)
        ctl.can_delete = lambda _item: True  # type: ignore[attr-defined]
        result = await ctl.execute_bulk_action("delete", ["1"])
        assert result == "Deleted 1 items"
        assert ds.bulk_delete_calls == [["1"]]

    async def test_purge_uses_purged_label(self) -> None:
        ds = _FakeDataSource({"1": {"id": 1}})
        ctl = _BulkController(ds)
        result = await ctl.execute_bulk_action("purge", ["1"])
        assert result == "Purged 1 items"
        assert ds.bulk_delete_calls == [["1"]]

    async def test_restore_sets_deleted_at_none(self) -> None:
        ds = _FakeDataSource({"1": {"id": 1}})
        ctl = _BulkController(ds)
        result = await ctl.execute_bulk_action("restore", ["1"])
        assert result == "Restored 1 items"
        assert ds.update_calls == [("1", {"deleted_at": None})]
        assert ds.bulk_delete_calls == []

    async def test_unknown_action(self) -> None:
        ds = _FakeDataSource()
        ctl = _BulkController(ds)
        assert (
            await ctl.execute_bulk_action("explode", ["1"]) == "Unknown action: explode"
        )
