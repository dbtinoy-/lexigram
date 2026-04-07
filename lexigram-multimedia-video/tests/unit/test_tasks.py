from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.video.tasks import VideoGenerationTask


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
