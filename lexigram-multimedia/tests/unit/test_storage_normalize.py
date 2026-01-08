from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.infra.storage.models import FileInfo
from lexigram.multimedia.storage_normalize import normalize_asset_dict


@pytest.mark.asyncio
async def test_bytes_result_is_uploaded_and_rewritten_to_url() -> None:
    store = AsyncMock()
    store.upload.return_value = FileInfo(
        path="multimedia/tts/x.mp3",
        size=3,
        content_type="audio/mpeg",
        last_modified=datetime.now(UTC),
    )
    store.get_url.return_value = "https://cdn.example/multimedia/tts/x.mp3"

    asset_dict = {
        "provider": "elevenlabs",
        "mime_type": "audio/mpeg",
        "bytes_data": b"abc",
        "uri": None,
        "metadata": {},
    }

    normalized = await normalize_asset_dict(
        asset_dict, store=store, path_prefix="multimedia/tts/", path_key="x.mp3"
    )

    store.upload.assert_awaited_once()
    assert normalized["uri"] == "https://cdn.example/multimedia/tts/x.mp3"
    assert normalized["bytes_data"] is None


@pytest.mark.asyncio
async def test_uri_result_passes_through_unchanged() -> None:
    store = AsyncMock()
    asset_dict = {
        "provider": "runway",
        "mime_type": "video/mp4",
        "bytes_data": None,
        "uri": "https://runway.example/out.mp4",
        "metadata": {},
    }

    normalized = await normalize_asset_dict(
        asset_dict, store=store, path_prefix="multimedia/video/", path_key="y.mp4"
    )

    store.upload.assert_not_awaited()
    assert normalized["uri"] == "https://runway.example/out.mp4"
