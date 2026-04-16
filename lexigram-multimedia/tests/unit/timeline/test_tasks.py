from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.timeline import Timeline
from lexigram.multimedia.timeline import TimelineRenderTask

CLIP = MediaAsset(mime_type="video/mp4", provider="local-http", uri="clip1.mp4")


@pytest.mark.asyncio
async def test_timeline_render_task_runs_and_returns_dict() -> None:
    processor = AsyncMock()
    processor.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"out")
    )
    task = TimelineRenderTask(processor=processor)

    timeline = Timeline().add_clip(CLIP)
    result = await task.run(timeline.to_params())

    assert result["bytes_data"] == b"out"
