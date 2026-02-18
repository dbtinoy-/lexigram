from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.interpolate.tasks import InterpolationTask


def _asset_params(provider: str) -> dict:
    return {"mime_type": "image/png", "provider": provider, "bytes_data": b"x"}


@pytest.mark.asyncio
async def test_task_calls_backend_interpolate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.interpolate.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="rife", bytes_data=b"x")
    )
    task = InterpolationTask(backend=backend)

    result = await task.run(
        {
            "frame_a": _asset_params("openai"),
            "frame_b": _asset_params("openai"),
        }
    )

    backend.interpolate.assert_awaited_once()
    assert result["provider"] == "rife"


@pytest.mark.asyncio
async def test_task_forwards_both_frames_and_extra_to_request() -> None:
    backend = AsyncMock()
    backend.interpolate.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="rife", bytes_data=b"x")
    )
    task = InterpolationTask(backend=backend)

    await task.run(
        {
            "frame_a": _asset_params("a-provider"),
            "frame_b": _asset_params("b-provider"),
            "extra": {"strength": "high"},
        }
    )

    sent_request = backend.interpolate.await_args.args[0]
    assert sent_request.frame_a.provider == "a-provider"
    assert sent_request.frame_b.provider == "b-provider"
    assert sent_request.extra == {"strength": "high"}
