from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.accessors import SubsystemAccessor


@pytest.mark.asyncio
async def test_generate_uses_configured_backend_method() -> None:
    fake_backend = AsyncMock()
    fake_backend.process.return_value = Ok(
        MediaAsset(mime_type="video/mp4", provider="ffmpeg", bytes_data=b"x")
    )
    accessor = SubsystemAccessor(
        backend=fake_backend,
        task_manager=None,
        task_name="video_processing",
        storage=None,
        path_prefix="video/processed/",
        backend_method="process",
    )
    result = await accessor.generate("some-operation")
    assert result.is_ok()
    fake_backend.process.assert_awaited_once_with("some-operation")
    fake_backend.generate.assert_not_called()
