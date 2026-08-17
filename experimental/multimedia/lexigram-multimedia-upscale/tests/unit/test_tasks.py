from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.upscale.tasks import UpscaleTask


@pytest.mark.asyncio
async def test_task_calls_backend_upscale_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.upscale.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="real-esrgan", bytes_data=b"x")
    )
    task = UpscaleTask(backend=backend)

    result = await task.run(
        {
            "asset": {
                "mime_type": "image/png",
                "provider": "openai",
                "bytes_data": b"y",
            },
            "scale_factor": 4,
        }
    )

    backend.upscale.assert_awaited_once()
    assert result["provider"] == "real-esrgan"


@pytest.mark.asyncio
async def test_task_forwards_scale_factor_and_extra_to_request() -> None:
    backend = AsyncMock()
    backend.upscale.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="hat", bytes_data=b"x")
    )
    task = UpscaleTask(backend=backend)

    await task.run(
        {
            "asset": {
                "mime_type": "image/png",
                "provider": "openai",
                "bytes_data": b"y",
            },
            "scale_factor": 2,
            "extra": {"denoise": "strong"},
        }
    )

    sent_request = backend.upscale.await_args.args[0]
    assert sent_request.scale_factor == 2
    assert sent_request.extra == {"denoise": "strong"}
    assert sent_request.asset.mime_type == "image/png"


@pytest.mark.asyncio
async def test_task_rejects_scale_factor_outside_2_4() -> None:
    backend = AsyncMock()
    task = UpscaleTask(backend=backend)

    with pytest.raises(ValueError, match="scale_factor must be 2 or 4"):
        await task.run(
            {
                "asset": {
                    "mime_type": "image/png",
                    "provider": "openai",
                    "bytes_data": b"y",
                },
                "scale_factor": 3,
            }
        )

    backend.upscale.assert_not_awaited()
