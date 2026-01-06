from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.image.tasks import ImageGenerationTask


@pytest.mark.asyncio
async def test_task_calls_backend_generate_and_returns_asset_dict() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="local-http", bytes_data=b"x")
    )
    task = ImageGenerationTask(backend=backend)

    result = await task.run(
        {"prompt": "a red rose", "width": 1024, "height": 1024, "format": "png"}
    )

    backend.generate.assert_awaited_once()
    assert result["provider"] == "local-http"
