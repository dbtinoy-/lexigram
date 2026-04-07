from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.services.export.scheduler import ExportFormat
from lexigram.admin.services.export.service import ExportService
from lexigram.admin.services.resource_manager import ResourceManager
from lexigram.contracts.audit import AuditQuery
from lexigram.testing.fakes import FakeAuditLogger


@dataclass
class _Resource:
    id: str
    name: str


class _ResourceDataSource:
    async def create(self, data: dict[str, object]) -> _Resource:
        return _Resource(id="r-1", name=str(data["name"]))

    async def find_one(self, item_id: object) -> _Resource | None:
        return _Resource(id=str(item_id), name="Widget")

    async def update(self, item_id: object, data: dict[str, object]) -> _Resource:
        return _Resource(id=str(item_id), name=str(data["name"]))

    async def delete(self, _item_id: object) -> bool:
        return True


@pytest.mark.asyncio
async def test_resource_manager_create_records_framework_audit() -> None:
    audit = FakeAuditLogger()
    manager = ResourceManager(
        resource_name="widgets",
        data_source=_ResourceDataSource(),
        audit=audit,
    )

    actor = SimpleNamespace(id="admin-1")
    result = await manager.create({"name": "Widget"}, user=actor)

    assert result.is_ok()
    events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.resource.create"))
    assert len(events) == 1
    assert events[0].resource_id == "r-1"


@pytest.mark.asyncio
async def test_resource_manager_update_records_framework_audit() -> None:
    audit = FakeAuditLogger()
    manager = ResourceManager(
        resource_name="widgets",
        data_source=_ResourceDataSource(),
        audit=audit,
    )

    actor = SimpleNamespace(id="admin-1")
    result = await manager.update("w-1", {"name": "Updated Widget"}, user=actor)

    assert result.is_ok()
    events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.resource.update"))
    assert len(events) == 1
    assert events[0].resource_id == "w-1"


@pytest.mark.asyncio
async def test_resource_manager_delete_records_framework_audit() -> None:
    audit = FakeAuditLogger()
    manager = ResourceManager(
        resource_name="widgets",
        data_source=_ResourceDataSource(),
        audit=audit,
    )

    actor = SimpleNamespace(id="admin-1")
    result = await manager.delete("w-1", user=actor)

    assert result.is_ok()
    events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.resource.delete"))
    assert len(events) == 1
    assert events[0].resource_id == "w-1"


@pytest.mark.asyncio
async def test_resource_manager_bulk_delete_fast_path_records_framework_audit() -> None:
    audit = FakeAuditLogger()

    class _DataSourceWithDeleteMany:
        async def delete_many(self, ids: list[object]) -> int:
            return len(ids)

    manager = ResourceManager(
        resource_name="widgets",
        data_source=_DataSourceWithDeleteMany(),
        audit=audit,
    )

    actor = SimpleNamespace(id="admin-1")
    result = await manager.bulk_delete(["w-1", "w-2", "w-3"], user=actor)

    assert result.is_ok()
    assert result.unwrap() == 3
    events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.resource.bulk_delete"))
    assert len(events) == 1
    assert events[0].resource_id == "bulk"
    assert events[0].metadata["deleted_count"] == 3
    assert events[0].metadata["requested_ids"] == 3


@pytest.mark.asyncio
async def test_resource_manager_bulk_delete_fallback_path_records_framework_audit() -> None:
    """Regression test: fallback bulk_delete should emit one bulk_delete event, not per-item delete events."""
    audit = FakeAuditLogger()

    class _DataSourceWithoutDeleteMany:
        async def find_one(self, item_id: object) -> _Resource | None:
            return _Resource(id=str(item_id), name="Widget")

        async def delete(self, _item_id: object) -> bool:
            return True

    manager = ResourceManager(
        resource_name="widgets",
        data_source=_DataSourceWithoutDeleteMany(),
        audit=audit,
    )

    actor = SimpleNamespace(id="admin-1")
    result = await manager.bulk_delete(["w-1", "w-2", "w-3"], user=actor)

    assert result.is_ok()
    assert result.unwrap() == 3

    bulk_events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.resource.bulk_delete"))
    assert len(bulk_events) == 1
    assert bulk_events[0].resource_id == "bulk"
    assert bulk_events[0].metadata["deleted_count"] == 3
    assert bulk_events[0].metadata["requested_ids"] == 3

    delete_events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.resource.delete"))
    assert len(delete_events) == 0


@pytest.mark.asyncio
async def test_export_service_records_successful_export() -> None:
    audit = FakeAuditLogger()
    storage = MagicMock()
    storage.upload = AsyncMock()
    task_manager = MagicMock()
    data_source = MagicMock()
    data_source.get_export_count = AsyncMock(return_value=1)
    data_source.get_export_data = AsyncMock(return_value=[{"id": "1", "name": "Ada"}])

    service = ExportService(storage=storage, task_manager=task_manager, audit=audit)
    job_id = service.create_job(
        resource_name="users",
        file_format=ExportFormat.JSON,
        user_id="admin-1",
    )

    result = await service.execute_export(job_id, data_source)

    assert result.is_ok()
    start_events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.export.start"))
    assert len(start_events) == 1
    complete_events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.export.complete"))
    assert len(complete_events) == 1


@pytest.mark.asyncio
async def test_export_service_records_failed_export_unsupported_format() -> None:
    audit = FakeAuditLogger()
    storage = MagicMock()
    storage.upload = AsyncMock()
    task_manager = MagicMock()
    data_source = MagicMock()

    service = ExportService(storage=storage, task_manager=task_manager, audit=audit)
    service._backends = {}

    job_id = service.create_job(
        resource_name="users",
        file_format=ExportFormat.JSON,
        user_id="admin-1",
    )

    result = await service.execute_export(job_id, data_source)

    assert result.is_err()
    failed_events = await audit.query(AuditQuery(actor_id="admin-1", action="admin.export.failed"))
    assert len(failed_events) == 1
    assert "Unsupported export format" in failed_events[0].metadata["error_message"]
