from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset, Trim
from lexigram.multimedia.accessors import SubsystemAccessor
from lexigram.multimedia.video_accessor import VideoAccessor


@pytest.mark.asyncio
async def test_process_delegates_to_processing_accessor() -> None:
    fake_backend = AsyncMock()
    fake_backend.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"x")
    )
    processing_accessor = SubsystemAccessor(
        backend=fake_backend,
        task_manager=None,
        task_name="video_processing",
        storage=None,
        path_prefix="video/processed/",
        backend_method="process",
    )
    generation_accessor = SubsystemAccessor(
        backend=AsyncMock(),
        task_manager=None,
        task_name="video_generation",
        storage=None,
        path_prefix="video/",
    )
    accessor = VideoAccessor(
        generation=generation_accessor,
        processing=processing_accessor,
        storage=None,
        path_prefix="video/processed/",
    )

    op = Trim(
        asset=MediaAsset(mime_type="video/mp4", provider="local-http", uri="a.mp4"),
        start=0.0,
        end=1.0,
    )
    result = await accessor.process(op)

    assert result.is_ok()
    fake_backend.process.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_process_normalizes_bytes_before_submitting() -> None:
    from datetime import UTC, datetime

    from lexigram.contracts.infra.storage.models import FileInfo
    from lexigram.multimedia.jobs import JobHandle

    fake_store = AsyncMock()
    fake_store.upload.return_value = FileInfo(
        path="video/processed/in/x.mp4",
        size=1,
        content_type="video/mp4",
        last_modified=datetime.now(UTC),
    )
    fake_store.get_url.return_value = "https://cdn.example/x.mp4"

    fake_task_manager = AsyncMock()
    fake_task_manager.submit_task.return_value = type(
        "R", (), {"status": "submitted", "task_id": "t1", "result": None}
    )()

    processing_accessor = SubsystemAccessor(
        backend=AsyncMock(),
        task_manager=fake_task_manager,
        task_name="video_processing",
        storage=fake_store,
        path_prefix="video/processed/",
        backend_method="process",
    )
    generation_accessor = SubsystemAccessor(
        backend=AsyncMock(),
        task_manager=fake_task_manager,
        task_name="video_generation",
        storage=fake_store,
        path_prefix="video/",
    )
    accessor = VideoAccessor(
        generation=generation_accessor,
        processing=processing_accessor,
        storage=fake_store,
        path_prefix="video/processed/in/",
    )

    op = Trim(
        asset=MediaAsset(
            mime_type="video/mp4", provider="local-http", bytes_data=b"raw"
        ),
        start=0.0,
        end=1.0,
    )
    handle = await accessor.submit_process(op)

    fake_store.upload.assert_awaited_once()
    assert isinstance(handle, JobHandle)
