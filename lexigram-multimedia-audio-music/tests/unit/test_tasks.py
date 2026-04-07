from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.audio_music.tasks import MusicGenerationTask


@pytest.mark.asyncio
async def test_task_calls_backend_generate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"x")
    )
    task = MusicGenerationTask(backend=backend)

    result = await task.run({"prompt": "lo-fi beats", "duration_seconds": 30.0, "format": "mp3"})

    backend.generate.assert_awaited_once()
    assert result["provider"] == "local-http"
