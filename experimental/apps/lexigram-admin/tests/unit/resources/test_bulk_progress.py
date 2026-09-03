"""R14 phase-2 live bulk progress tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.progress import (
    LocalProgressTracker,
    ProgressAccessRegistry,
    ProgressController,
    progress_principal_key,
)
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.handler import BulkActionHandler
from lexigram.contracts.infra.tasks.progress import ProgressSnapshot, ProgressStatus
from lexigram.serialization import loads


class _DataSource:
    def __init__(self, count: int = 2) -> None:
        self.records = {str(i): {"id": str(i)} for i in range(count)}
        self.deleted: list[str] = []
        self.started = asyncio.Event()

    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return self.records.get(str(item_id))

    async def delete(self, item_id: Any) -> bool:
        self.started.set()
        key = str(item_id)
        self.records.pop(key, None)
        self.deleted.append(key)
        await asyncio.sleep(0)
        return True

    async def update(
        self, item_id: Any, values: dict[str, Any]
    ) -> dict[str, Any] | None:
        record = self.records.get(str(item_id))
        if record is None:
            return None
        record.update(values)
        return record


class _Items(Resource):
    name = "items"


def _request(
    form: dict[str, Any],
    *,
    tracker: Any | None = None,
    access: Any | None = None,
    user: Any = None,
    prefix: str = "/admin",
    htmx: bool = True,
) -> Request:
    headers = [(b"hx-request", b"true")] if htmx else []
    app_state = SimpleNamespace(
        progress_tracker=tracker,
        progress_access=access,
        admin_prefix=prefix,
    )
    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": f"{prefix}/items/bulk",
        "query_string": b"",
        "headers": headers,
        "path_params": {},
        "app": SimpleNamespace(state=app_state),
        "state": {
            "user": user,
            "permissions": {"can_delete": True, "can_update": True},
        },
    }
    request = Request(scope)
    form_obj = MagicMock()
    form_obj.get = lambda key, default=None: form.get(key, default)
    form_obj.getlist = lambda key: form.get(f"{key}__list", [])
    request.scope["admin_form_data"] = form_obj
    return request


def _resource(data_source: _DataSource) -> _Items:
    resource = _Items()
    resource._data_source = data_source
    return resource


def test_progress_principal_key_uses_session_identity() -> None:
    request = _request({}, user=None)
    request.scope["session"] = {"admin_user_id": "session-operator"}

    assert progress_principal_key(request) == "session:session-operator"


def test_progress_access_capacity_does_not_evict_existing_owner() -> None:
    access = ProgressAccessRegistry(max_entries=1)

    assert access.register("first", "user:one")
    assert not access.register("second", "user:two")
    assert not access.is_allowed("first", "user:two")
    assert access.is_allowed("first", "user:one")


@pytest.mark.asyncio
async def test_large_htmx_delete_returns_start_event_and_finishes_with_metadata() -> (
    None
):
    data_source = _DataSource(count=20)
    tracker = LocalProgressTracker()
    access = ProgressAccessRegistry()
    handler = BulkActionHandler()
    request = _request(
        {
            "action": "delete",
            "ids__list": [str(i) for i in range(20)],
        },
        tracker=tracker,
        access=access,
        user={"id": "operator-1"},
        prefix="/console",
    )

    response = await handler.handle(request, _resource(data_source))

    assert response.status_code == 202
    payload = loads(response.headers["HX-Trigger"])["bulk-progress-start"]
    assert payload["total"] == 20
    assert payload["status_url"].startswith("/console/progress/")
    assert payload["stream_url"].endswith("/stream")
    assert data_source.deleted == []
    task_id = payload["task_id"]
    assert access.is_allowed(task_id, "user:operator-1")
    assert not access.is_allowed(task_id, "user:other")

    # Let the strongly-held background task finish and inspect the terminal
    # snapshot that the SSE/status controller will expose.
    await asyncio.gather(*list(handler._background_tasks))
    snapshot = await tracker.get(task_id)
    assert snapshot is not None
    assert snapshot.status is ProgressStatus.COMPLETE
    assert snapshot.current == 20
    assert snapshot.message == "Deleted 20 item(s)"
    assert snapshot.metadata["toast_type"] == "success"
    assert len(data_source.deleted) == 20


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["purge", "restore"])
async def test_large_archive_actions_use_the_progress_path(action: str) -> None:
    data_source = _DataSource(count=20)
    tracker = LocalProgressTracker()
    access = ProgressAccessRegistry()
    request = _request(
        {"action": action, "ids__list": [str(i) for i in range(20)]},
        tracker=tracker,
        access=access,
        user={"id": "operator-1"},
    )
    handler = BulkActionHandler()

    response = await handler.handle(request, _resource(data_source))
    await asyncio.gather(*list(handler._background_tasks))

    task_id = loads(response.headers["HX-Trigger"])["bulk-progress-start"]["task_id"]
    snapshot = await tracker.get(task_id)
    assert response.status_code == 202
    assert snapshot is not None
    assert snapshot.status is ProgressStatus.COMPLETE
    assert snapshot.current == 20
    assert (
        snapshot.message
        == f"{'Purged' if action == 'purge' else 'Restored'} 20 item(s)"
    )
    if action == "purge":
        assert data_source.records == {}
    else:
        assert len(data_source.records) == 20


@pytest.mark.asyncio
async def test_large_batch_counts_row_failures_in_terminal_snapshot() -> None:
    class FlakyDataSource(_DataSource):
        async def delete(self, item_id: Any) -> bool:
            if str(item_id) == "3":
                raise RuntimeError("simulated storage failure")
            return await super().delete(item_id)

    data_source = FlakyDataSource(count=20)
    tracker = LocalProgressTracker()
    access = ProgressAccessRegistry()
    request = _request(
        {"action": "delete", "ids__list": [str(i) for i in range(20)]},
        tracker=tracker,
        access=access,
        user={"id": "operator-1"},
    )
    handler = BulkActionHandler()

    response = await handler.handle(request, _resource(data_source))
    await asyncio.gather(*list(handler._background_tasks))

    task_id = loads(response.headers["HX-Trigger"])["bulk-progress-start"]["task_id"]
    snapshot = await tracker.get(task_id)
    assert snapshot is not None
    assert snapshot.status is ProgressStatus.COMPLETE
    assert snapshot.current == 20
    assert snapshot.message.startswith("Deleted 19 of 20 item(s) - 1 failed:")
    assert snapshot.metadata["toast_type"] == "warning"
    assert snapshot.metadata["duration"] == 8000
    assert len(data_source.deleted) == 19


@pytest.mark.asyncio
async def test_under_threshold_remains_synchronous() -> None:
    data_source = _DataSource(count=2)
    tracker = LocalProgressTracker()
    access = ProgressAccessRegistry()
    request = _request(
        {"action": "delete", "ids__list": ["0", "1"]},
        tracker=tracker,
        access=access,
        user={"id": "operator-1"},
    )

    response = await BulkActionHandler().handle(request, _resource(data_source))

    assert response.status_code == 200
    assert "bulk-progress-start" not in response.headers
    assert loads(response.headers["HX-Trigger"])["show-toast"]["message"] == (
        "Deleted 2 item(s)"
    )
    assert len(data_source.deleted) == 2


@pytest.mark.asyncio
async def test_tracker_start_failure_falls_back_to_synchronous_mutation() -> None:
    class BrokenTracker(LocalProgressTracker):
        async def update(
            self, task_id: str, current: int, total: int, message: str = ""
        ) -> None:
            raise RuntimeError("tracker unavailable")

    data_source = _DataSource(count=20)
    access = ProgressAccessRegistry()
    request = _request(
        {"action": "delete", "ids__list": [str(i) for i in range(20)]},
        tracker=BrokenTracker(),
        access=access,
        user={"id": "operator-1"},
    )

    response = await BulkActionHandler().handle(request, _resource(data_source))

    assert response.status_code == 200
    assert "bulk-progress-start" not in response.headers
    assert len(data_source.deleted) == 20


@pytest.mark.asyncio
async def test_legacy_tracker_without_metadata_keyword_still_completes() -> None:
    class LegacyTracker(LocalProgressTracker):
        async def complete(self, task_id: str, result: str = "") -> None:
            await super().complete(task_id, result)

    data_source = _DataSource(count=20)
    tracker = LegacyTracker()
    access = ProgressAccessRegistry()
    request = _request(
        {"action": "delete", "ids__list": [str(i) for i in range(20)]},
        tracker=tracker,
        access=access,
        user={"id": "operator-1"},
    )
    handler = BulkActionHandler()

    response = await handler.handle(request, _resource(data_source))
    await asyncio.gather(*list(handler._background_tasks))

    task_id = loads(response.headers["HX-Trigger"])["bulk-progress-start"]["task_id"]
    snapshot = await tracker.get(task_id)
    assert response.status_code == 202
    assert snapshot is not None
    assert snapshot.status is ProgressStatus.COMPLETE
    assert len(data_source.deleted) == 20


@pytest.mark.asyncio
async def test_progress_controller_serializes_terminal_metadata() -> None:
    tracker = LocalProgressTracker()
    await tracker.update("bulk-meta", 1, 1, "working")
    await tracker.complete(
        "bulk-meta",
        "done",
        {"toast_type": "success", "duration": 3000, "refresh": True},
    )
    controller = ProgressController(tracker=tracker)
    request = _request({}, user={"id": "operator-1"})
    request.scope["path_params"] = {"task_id": "bulk-meta"}

    result = await controller.get_task_status(request)

    assert isinstance(result, dict)
    assert result["metadata"] == {
        "toast_type": "success",
        "duration": 3000,
        "refresh": True,
    }


@pytest.mark.asyncio
async def test_progress_controller_hides_registered_task_from_other_principal() -> None:
    tracker = LocalProgressTracker()
    access = ProgressAccessRegistry()
    await tracker.update("bulk-secret", 1, 2, "working")
    assert access.register("bulk-secret", "user:one")
    controller = ProgressController(tracker=tracker, access_registry=access)

    owner = _request({}, tracker=tracker, access=access, user={"id": "one"})
    owner.scope["path_params"] = {"task_id": "bulk-secret"}
    other = _request({}, tracker=tracker, access=access, user={"id": "two"})
    other.scope["path_params"] = {"task_id": "bulk-secret"}

    owner_status = await controller.get_task_status(owner)
    other_status = await controller.get_task_status(other)
    assert isinstance(owner_status, dict)
    assert owner_status["id"] == "bulk-secret"
    assert other_status == ({"error": "Task not found"}, 404)

    stream = await controller.stream_progress(other)
    assert stream.status_code == 404
    body = "".join([chunk async for chunk in stream.body_iterator])
    assert "Task not found" in body


@pytest.mark.asyncio
async def test_terminal_metadata_is_preserved_by_local_tracker() -> None:
    tracker = LocalProgressTracker()
    await tracker.update("job", 0, 1)
    await tracker.complete(
        "job", "finished", {"toast_type": "warning", "refresh": True}
    )
    snapshot = await tracker.get("job")
    assert snapshot == ProgressSnapshot(
        task_id="job",
        current=1,
        total=1,
        status=ProgressStatus.COMPLETE,
        message="finished",
        metadata={"toast_type": "warning", "refresh": True},
    )
