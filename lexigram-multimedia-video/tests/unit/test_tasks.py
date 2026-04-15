from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.video.tasks import VideoGenerationTask, VideoProcessingTask


@pytest.mark.asyncio
async def test_task_calls_backend_generate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="local-http", bytes_data=b"x")
    )
    task = VideoGenerationTask(backend=backend)

    result = await task.run(
        {
            "prompt": "a drone over the valley",
            "duration_seconds": 4.0,
            "resolution": "1280x720",
            "format": "mp4",
        }
    )

    backend.generate.assert_awaited_once()
    assert result["provider"] == "local-http"


@pytest.mark.asyncio
async def test_video_processing_task_trim() -> None:
    fake_backend = AsyncMock()
    fake_backend.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"out")
    )
    task = VideoProcessingTask(backend=fake_backend)

    result = await task.run(
        {
            "operation_type": "Trim",
            "asset": {
                "mime_type": "video/mp4",
                "provider": "local-http",
                "uri": "a.mp4",
            },
            "start": 1.0,
            "end": 2.0,
        }
    )

    assert result["bytes_data"] == b"out"
    fake_backend.process.assert_awaited_once()
    called_op = fake_backend.process.call_args[0][0]
    assert called_op.start == 1.0
    assert called_op.end == 2.0
