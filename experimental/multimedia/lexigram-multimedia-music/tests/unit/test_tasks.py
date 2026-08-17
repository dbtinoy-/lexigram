from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.music.tasks import MusicGenerationTask


@pytest.mark.asyncio
async def test_task_calls_backend_generate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"x")
    )
    task = MusicGenerationTask(backend=backend)

    result = await task.run(
        {"prompt": "lo-fi beats", "duration_seconds": 30.0, "format": "mp3"}
    )

    backend.generate.assert_awaited_once()
    assert result["provider"] == "local-http"


@pytest.mark.asyncio
async def test_task_forwards_extra_to_request() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/wav", provider="ace-step", bytes_data=b"x")
    )
    task = MusicGenerationTask(backend=backend)

    await task.run(
        {
            "prompt": "an upbeat synthwave track",
            "duration_seconds": 30.0,
            "format": "wav",
            "extra": {"tags": "synthwave, upbeat, 120bpm", "lyrics": ""},
        }
    )

    sent_request = backend.generate.await_args.args[0]
    assert sent_request.extra == {"tags": "synthwave, upbeat, 120bpm", "lyrics": ""}
