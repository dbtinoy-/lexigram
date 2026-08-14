from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.tts.tasks import TTSGenerationTask


@pytest.mark.asyncio
async def test_task_calls_backend_generate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"x")
    )
    task = TTSGenerationTask(backend=backend)

    result = await task.run({"text": "hello", "voice": None, "format": "mp3"})

    backend.generate.assert_awaited_once()
    assert result["provider"] == "local-http"


@pytest.mark.asyncio
async def test_task_forwards_extra_to_request() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/wav", provider="f5-tts", bytes_data=b"x")
    )
    task = TTSGenerationTask(backend=backend)

    await task.run(
        {
            "text": "hello",
            "voice": None,
            "format": "wav",
            "extra": {"reference_audio_uri": "file:///tmp/ref.wav", "reference_text": "hi"},
        }
    )

    sent_request = backend.generate.await_args.args[0]
    assert sent_request.extra == {
        "reference_audio_uri": "file:///tmp/ref.wav",
        "reference_text": "hi",
    }
