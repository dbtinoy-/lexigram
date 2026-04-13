"""Tests for PurgeBulkAction, RestoreBulkAction, CloneAction hooks,
ImportAction example CSV, and bulk purge/restore wiring.

Covers the data-driven execution paths (chunked purge, per-id restore),
Filament Replicate parity hooks on CloneAction, the ImportAction example
template download, and the confirmation slide-over rendering used by the
new bulk actions.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.actions.base import BulkAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.standard import (
    CloneAction,
    ImportAction,
    PurgeBulkAction,
    RestoreBulkAction,
)
from lexigram.admin.actions.types import ActionColor, ActionContext
from lexigram.admin.ui.organisms.admin_slide_over import render_bulk_delete_confirm


class _FakeDataSource:
    """In-memory IDataSource fake tracking every call."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self.bulk_delete_calls: list[list[str]] = []
        self.update_calls: list[tuple[str, dict[str, Any]]] = []
        self.create_calls: list[dict[str, Any]] = []
        self.find_one_calls: list[Any] = []

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        self.find_one_calls.append(item_id)
        return self._store.get(str(item_id))

    async def create(self, data: dict[str, Any]) -> dict[str, Any] | None:
        self.create_calls.append(data)
        record = {"id": f"new-{len(self.create_calls)}", **data}
        self._store[record["id"]] = record
        return record

    async def update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any] | None:
        self.update_calls.append((str(item_id), data))
        record = self._store.get(str(item_id))
        if record is None:
            return None
        record.update(data)
        return record

    async def delete(self, item_id: Any) -> bool:
        return self._store.pop(str(item_id), None) is not None

    async def bulk_delete(self, ids: list[str]) -> int:
        self.bulk_delete_calls.append(list(ids))
        deleted = 0
        for id_ in ids:
            if self._store.pop(str(id_), None) is not None:
                deleted += 1
        return deleted


class TestPurgeBulkAction:
    """Tests for PurgeBulkAction."""

    def test_defaults(self) -> None:
        action = PurgeBulkAction()
        assert action.name == "purge"
        assert action.label == "Purge Selected"
        assert action.icon == "trash-2"
        assert action.color == ActionColor.DANGER
        assert isinstance(action, BulkAction)

    def test_custom_label(self) -> None:
        action = PurgeBulkAction(label="Erase")
        assert action.label == "Erase"

    def test_has_confirmation(self) -> None:
        action = PurgeBulkAction()
        config = action.confirm()
        assert config is not None
        assert config.title == "Purge Selected Records"
        assert config.style == ActionColor.DANGER

    def test_htmx_attrs_use_bulk_purge_confirm(self) -> None:
        action = PurgeBulkAction()
        ctx = ActionContext(resource_name="users")
        attrs = action._get_htmx_attrs("", [], ctx)
        assert attrs["hx-get"] == "/users/bulk-purge-confirm"
        assert attrs["hx-target"] == "#slide-over-container"

    @pytest.mark.asyncio
    async def test_execute_chunks_bulk_delete(self) -> None:
        ds = _FakeDataSource()
        for i in range(5):
            ds._store[str(i)] = {"id": str(i)}
        action = PurgeBulkAction(data_source=ds, chunk_size=2)
        ctx = ActionContext(resource_name="users")
        records = [{"id": str(i)} for i in range(5)]
        result = await action.execute(records, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert value["purged_count"] == 5
        assert "Purged 5 record(s)" in value["message"]
        assert ds.bulk_delete_calls == [["0", "1"], ["2", "3"], ["4"]]

    @pytest.mark.asyncio
    async def test_execute_uses_context_data_source(self) -> None:
        ds = _FakeDataSource()
        ds._store["a"] = {"id": "a"}
        ds._store["b"] = {"id": "b"}
        action = PurgeBulkAction()
        ctx = ActionContext(resource_name="users", data_source=ds)
        result = await action.execute([{"id": "a"}, {"id": "b"}], ctx)
        assert result.is_ok()
        assert result.unwrap()["purged_count"] == 2

    @pytest.mark.asyncio
    async def test_execute_extracts_ids_from_objects(self) -> None:
        class Record:
            def __init__(self, id: str) -> None:
                self.id = id

        ds = _FakeDataSource()
        ds._store["x"] = {"id": "x"}
        ds._store["y"] = {"id": "y"}
        action = PurgeBulkAction(data_source=ds)
        ctx = ActionContext(resource_name="users")
        result = await action.execute([Record("x"), Record("y")], ctx)
        assert result.is_ok()
        assert result.unwrap()["purged_count"] == 2

    @pytest.mark.asyncio
    async def test_execute_empty_ids(self) -> None:
        ds = _FakeDataSource()
        action = PurgeBulkAction(data_source=ds)
        ctx = ActionContext(resource_name="users")
        result = await action.execute([{"no_id": 1}], ctx)
        assert result.is_ok()
        assert result.unwrap()["purged_count"] == 0
        assert ds.bulk_delete_calls == []

    @pytest.mark.asyncio
    async def test_execute_missing_data_source_returns_err(self) -> None:
        action = PurgeBulkAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute([{"id": 1}], ctx)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)


class TestRestoreBulkAction:
    """Tests for RestoreBulkAction."""

    def test_defaults(self) -> None:
        action = RestoreBulkAction()
        assert action.name == "restore"
        assert action.label == "Restore Selected"
        assert action.icon == "rotate-ccw"
        assert action.color == ActionColor.SUCCESS
        assert isinstance(action, BulkAction)

    def test_has_confirmation(self) -> None:
        action = RestoreBulkAction()
        config = action.confirm()
        assert config is not None
        assert config.title == "Restore Selected Records"
        assert config.style == ActionColor.SUCCESS

    def test_htmx_attrs_use_bulk_restore_confirm(self) -> None:
        action = RestoreBulkAction()
        ctx = ActionContext(resource_name="users")
        attrs = action._get_htmx_attrs("", [], ctx)
        assert attrs["hx-get"] == "/users/bulk-restore-confirm"
        assert attrs["hx-target"] == "#slide-over-container"

    @pytest.mark.asyncio
    async def test_execute_clears_deleted_at_per_record(self) -> None:
        ds = _FakeDataSource()
        ds._store["a"] = {"id": "a", "deleted_at": "2026-01-01"}
        ds._store["b"] = {"id": "b", "deleted_at": "2026-01-01"}
        action = RestoreBulkAction(data_source=ds)
        ctx = ActionContext(resource_name="users")
        result = await action.execute([{"id": "a"}, {"id": "b"}], ctx)
        assert result.is_ok()
        assert result.unwrap()["restored_count"] == 2
        assert ds.update_calls == [
            ("a", {"deleted_at": None}),
            ("b", {"deleted_at": None}),
        ]

    @pytest.mark.asyncio
    async def test_execute_counts_only_existing_records(self) -> None:
        ds = _FakeDataSource()
        action = RestoreBulkAction(data_source=ds)
        ctx = ActionContext(resource_name="users")
        result = await action.execute([{"id": "missing"}, {"id": "also-missing"}], ctx)
        assert result.is_ok()
        assert result.unwrap()["restored_count"] == 0
        assert "Restored 0 record(s)" in result.unwrap()["message"]

    @pytest.mark.asyncio
    async def test_execute_missing_data_source_returns_err(self) -> None:
        action = RestoreBulkAction()
        ctx = ActionContext(resource_name="users")
        result = await action.execute([{"id": 1}], ctx)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)


class TestCloneActionReplicateParity:
    """Tests for CloneAction Filament Replicate parity hooks."""

    @pytest.mark.asyncio
    async def test_execute_strips_id_and_copies(self) -> None:
        ds = _FakeDataSource()
        ds._store["1"] = {"id": "1", "name": "Widget", "price": 10}
        action = CloneAction(data_source=ds)
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "1"}, ctx)
        assert result.is_ok()
        value = result.unwrap()
        assert value["cloned_id"] == "new-1"
        assert value["record"]["name"] == "Widget"
        assert ds.create_calls == [{"name": "Widget", "price": 10}]

    @pytest.mark.asyncio
    async def test_execute_applies_exclude_attributes(self) -> None:
        ds = _FakeDataSource()
        ds._store["1"] = {"id": "1", "name": "Widget", "secret": "x", "price": 10}
        action = CloneAction(data_source=ds, exclude_attributes=["secret"])
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "1"}, ctx)
        assert result.is_ok()
        assert "secret" not in ds.create_calls[0]
        assert ds.create_calls[0]["price"] == 10

    @pytest.mark.asyncio
    async def test_execute_applies_mutate_record_data_sync(self) -> None:
        ds = _FakeDataSource()
        ds._store["1"] = {"id": "1", "name": "Widget"}
        action = CloneAction(
            data_source=ds,
            mutate_record_data=lambda data: {**data, "name": f"{data['name']} (Copy)"},
        )
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "1"}, ctx)
        assert result.is_ok()
        assert ds.create_calls[0]["name"] == "Widget (Copy)"

    @pytest.mark.asyncio
    async def test_execute_applies_mutate_record_data_async(self) -> None:
        ds = _FakeDataSource()
        ds._store["1"] = {"id": "1", "name": "Widget"}

        async def mutate(data: dict[str, Any]) -> dict[str, Any]:
            return {**data, "name": "Async Copy"}

        action = CloneAction(data_source=ds, mutate_record_data=mutate)
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "1"}, ctx)
        assert result.is_ok()
        assert ds.create_calls[0]["name"] == "Async Copy"

    @pytest.mark.asyncio
    async def test_execute_calls_before_replica_saved(self) -> None:
        ds = _FakeDataSource()
        ds._store["1"] = {"id": "1", "name": "Widget"}
        seen: list[dict[str, Any]] = []

        def before(data: dict[str, Any]) -> None:
            seen.append(data)

        action = CloneAction(data_source=ds, before_replica_saved=before)
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "1"}, ctx)
        assert result.is_ok()
        assert seen == [{"name": "Widget"}]

    @pytest.mark.asyncio
    async def test_execute_supports_async_before_replica_saved(self) -> None:
        ds = _FakeDataSource()
        ds._store["1"] = {"id": "1", "name": "Widget"}
        seen: list[dict[str, Any]] = []

        async def before(data: dict[str, Any]) -> None:
            seen.append(data)

        action = CloneAction(data_source=ds, before_replica_saved=before)
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "1"}, ctx)
        assert result.is_ok()
        assert seen == [{"name": "Widget"}]

    @pytest.mark.asyncio
    async def test_execute_not_found_returns_err(self) -> None:
        ds = _FakeDataSource()
        action = CloneAction(data_source=ds)
        ctx = ActionContext(resource_name="products")
        result = await action.execute({"id": "missing"}, ctx)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), ActionError)


class TestImportActionExampleCsv:
    """Tests for ImportAction example CSV template download."""

    def test_example_csv_header_only(self) -> None:
        action = ImportAction(example_columns=["name", "email", "role"])
        assert action.example_csv() == "name,email,role\n"

    def test_example_csv_quotes_embedded_commas(self) -> None:
        action = ImportAction(example_columns=["display, name", "email"])
        assert action.example_csv() == '"display, name",email\n'

    def test_example_csv_empty_without_columns(self) -> None:
        action = ImportAction()
        assert action.example_csv() == ""

    def test_example_filename_default(self) -> None:
        action = ImportAction()
        assert action._example_filename == "import-example.csv"

    def test_example_filename_custom(self) -> None:
        action = ImportAction(example_filename="users-template.csv")
        assert action._example_filename == "users-template.csv"


class TestRenderBulkDeleteConfirmParams:
    """Tests for the parameterized bulk confirm slide-over rendering."""

    def test_delete_defaults_unchanged(self) -> None:
        html = render_bulk_delete_confirm(record_count=2, bulk_url="/admin/users/bulk")
        assert "Confirm Bulk Deletion" in html
        assert "Type" in html
        assert "DELETE" in html
        assert "{&quot;action&quot;:&quot;delete&quot;}" in html
        assert "Delete Records" in html

    def test_purge_rendering(self) -> None:
        html = render_bulk_delete_confirm(
            record_count=2,
            bulk_url="/admin/users/bulk",
            action="purge",
            title="Purge Records",
            heading="Confirm Bulk Purge",
            confirm_phrase="PURGE",
            confirm_label="Purge",
        )
        assert "Confirm Bulk Purge" in html
        assert "PURGE" in html
        assert "{&quot;action&quot;:&quot;purge&quot;}" in html
        assert "Purge Records" in html

    def test_restore_rendering(self) -> None:
        html = render_bulk_delete_confirm(
            record_count=1,
            bulk_url="/admin/users/bulk",
            action="restore",
            title="Restore Records",
            heading="Confirm Bulk Restore",
            confirm_phrase="RESTORE",
            confirm_label="Restore",
        )
        assert "Confirm Bulk Restore" in html
        assert "RESTORE" in html
        assert "{&quot;action&quot;:&quot;restore&quot;}" in html
        assert "Restore Records" in html
