from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Err, Ok
from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.contracts.multimedia.types import (
    BeatAnalysisRequest,
    BeatAnalysisResult,
    MediaAsset,
)
from lexigram.multimedia.accessors import BeatAccessor


@pytest.mark.asyncio
async def test_analyze_delegates_to_backend_analyze() -> None:
    fake_backend = AsyncMock()
    fake_backend.analyze.return_value = Ok(
        BeatAnalysisResult(tempo_bpm=128.0, beat_timestamps=[0.0, 0.47, 0.94])
    )
    accessor = BeatAccessor(backend=fake_backend)

    asset = MediaAsset(mime_type="audio/wav", provider="local-http", bytes_data=b"x")
    request = BeatAnalysisRequest(asset=asset)
    result = await accessor.analyze(request)

    assert result.is_ok()
    assert result.unwrap() == BeatAnalysisResult(
        tempo_bpm=128.0, beat_timestamps=[0.0, 0.47, 0.94]
    )
    fake_backend.analyze.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_analyze_propagates_backend_error() -> None:
    fake_backend = AsyncMock()
    fake_backend.analyze.return_value = Err(MultimediaError("boom"))
    accessor = BeatAccessor(backend=fake_backend)

    asset = MediaAsset(mime_type="audio/wav", provider="local-http", bytes_data=b"x")
    result = await accessor.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
