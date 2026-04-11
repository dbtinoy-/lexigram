from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.multimedia.types import TTSRequest
from lexigram.multimedia.accessors import SubsystemAccessor
from lexigram.multimedia.jobs import JobHandle


def _fake_idempotency_manager(check_returns: object | None) -> AsyncMock:
    mgr = AsyncMock()
    mgr.generate_key.return_value = "idempotency:tts_generation:abc123"
    mgr.check_duplicate.return_value = check_returns
    return mgr


def _job_handle_result(status: str, task_id: str = "task-1") -> object:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, task_id=task_id, is_duplicate=False)


@pytest.mark.asyncio
async def test_submit_returns_fresh_job_handle_when_no_duplicate() -> None:
    task_manager = AsyncMock()
    task_manager.submit_task.return_value = _job_handle_result("submitted")
    idem = _fake_idempotency_manager(check_returns=None)
    accessor = SubsystemAccessor(
        backend=AsyncMock(),
        task_manager=task_manager,
        task_name="tts_generation",
        storage=None,
        path_prefix="multimedia/tts/",
        idempotency_manager=idem,
    )

    handle = await accessor.submit(TTSRequest(text="hi"))

    assert isinstance(handle, JobHandle)
    assert handle.is_duplicate is False
    task_manager.submit_task.assert_awaited_once_with(
        "tts_generation",
        {"text": "hi", "voice": None, "format": "mp3", "extra": {}},
        idempotency_key=None,
    )


@pytest.mark.asyncio
async def test_submit_marks_duplicate_when_preexisting_record() -> None:
    task_manager = AsyncMock()
    task_manager.submit_task.return_value = _job_handle_result("submitted")
    idem = _fake_idempotency_manager(check_returns={"status": "submitted"})
    accessor = SubsystemAccessor(
        backend=AsyncMock(),
        task_manager=task_manager,
        task_name="tts_generation",
        storage=None,
        path_prefix="multimedia/tts/",
        idempotency_manager=idem,
    )

    handle = await accessor.submit(TTSRequest(text="hi"), idempotency_key="client-key")

    assert handle.is_duplicate is True
    idem.generate_key.assert_called_once()


@pytest.mark.asyncio
async def test_submit_without_idempotency_manager_is_not_duplicate() -> None:
    task_manager = AsyncMock()
    task_manager.submit_task.return_value = _job_handle_result("submitted")
    accessor = SubsystemAccessor(
        backend=AsyncMock(),
        task_manager=task_manager,
        task_name="tts_generation",
        storage=None,
        path_prefix="multimedia/tts/",
        idempotency_manager=None,
    )

    handle = await accessor.submit(TTSRequest(text="hi"))

    assert isinstance(handle, JobHandle)
    assert handle.is_duplicate is False
