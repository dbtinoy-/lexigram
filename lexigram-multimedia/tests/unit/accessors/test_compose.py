from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.accessors import ComposeAccessor
from lexigram.multimedia.timeline import Timeline

CLIP = MediaAsset(mime_type="video/mp4", provider="local-http", uri="clip1.mp4")


@pytest.mark.asyncio
async def test_render_calls_timeline_render_directly() -> None:
    processor = AsyncMock()
    processor.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", uri="out.mp4")
    )
    accessor = ComposeAccessor(
        processor=processor,
        task_manager=AsyncMock(),
        task_name="timeline_render",
        storage=None,
        path_prefix="video/composed/",
    )

    timeline = Timeline().add_clip(CLIP)
    result = await accessor.render(timeline)

    assert result.is_ok()
    processor.process.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_render_normalizes_and_submits() -> None:
    from datetime import UTC, datetime

    from lexigram.contracts.infra.storage.models import FileInfo
    from lexigram.multimedia.types import JobHandle

    fake_store = AsyncMock()
    fake_store.upload.return_value = FileInfo(
        path="video/composed/in/x.mp4",
        size=1,
        content_type="video/mp4",
        last_modified=datetime.now(UTC),
    )
    fake_store.get_url.return_value = "https://cdn.example/x.mp4"

    fake_task_manager = AsyncMock()
    fake_task_manager.submit_task.return_value = type(
        "R", (), {"status": "submitted", "task_id": "t1", "result": None}
    )()

    accessor = ComposeAccessor(
        processor=AsyncMock(),
        task_manager=fake_task_manager,
        task_name="timeline_render",
        storage=fake_store,
        path_prefix="video/composed/in/",
    )

    timeline = Timeline().add_clip(
        MediaAsset(mime_type="video/mp4", provider="local-http", bytes_data=b"raw")
    )

    handle = await accessor.submit_render(timeline)

    fake_store.upload.assert_awaited_once()
    assert isinstance(handle, JobHandle)


@pytest.mark.asyncio
async def test_submit_render_preserves_clip_transitions() -> None:
    from datetime import UTC, datetime

    from lexigram.contracts.infra.storage.models import FileInfo
    from lexigram.contracts.multimedia.types import TransitionSpec

    fake_store = AsyncMock()
    fake_store.upload.return_value = FileInfo(
        path="video/composed/in/x.mp4",
        size=1,
        content_type="video/mp4",
        last_modified=datetime.now(UTC),
    )
    fake_store.get_url.return_value = "https://cdn.example/x.mp4"

    fake_task_manager = AsyncMock()
    fake_task_manager.submit_task.return_value = type(
        "R", (), {"status": "submitted", "task_id": "t1", "result": None}
    )()

    accessor = ComposeAccessor(
        processor=AsyncMock(),
        task_manager=fake_task_manager,
        task_name="timeline_render",
        storage=fake_store,
        path_prefix="video/composed/in/",
    )

    timeline = (
        Timeline()
        .add_clip(
            MediaAsset(mime_type="video/mp4", provider="local-http", bytes_data=b"raw")
        )
        .add_clip(
            MediaAsset(
                mime_type="video/mp4", provider="local-http", bytes_data=b"raw2"
            ),
            transition_in=TransitionSpec(kind="crossfade", duration=0.5),
        )
    )

    await accessor.submit_render(timeline)

    submitted_params = fake_task_manager.submit_task.call_args[0][1]
    assert submitted_params["transitions"] == [{"kind": "crossfade", "duration": 0.5}]
