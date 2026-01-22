from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.infra.storage.models import FileInfo
from lexigram.contracts.multimedia.types import MediaAsset, Trim
from lexigram.multimedia.storage import normalize_asset_dict, normalize_operation_assets


@pytest.mark.asyncio
async def test_normalize_operation_assets_uploads_bytes() -> None:
    fake_store = AsyncMock()
    fake_store.upload.return_value = FileInfo(
        path="multimedia/video/processed/in/x.mp4",
        size=1,
        content_type="video/mp4",
        last_modified=datetime.now(UTC),
    )
    fake_store.get_url.return_value = "https://cdn.example/x.mp4"

    op = Trim(
        asset=MediaAsset(
            mime_type="video/mp4", provider="local-http", bytes_data=b"raw"
        ),
        start=0.0,
        end=1.0,
    )
    normalized = await normalize_operation_assets(
        op, storage=fake_store, path_prefix="video/processed/in/"
    )

    assert normalized.asset.uri == "https://cdn.example/x.mp4"
    assert normalized.asset.bytes_data is None
    assert normalized.start == 0.0
    assert normalized.end == 1.0
    fake_store.upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_normalize_operation_assets_passthrough_without_storage() -> None:
    op = Trim(
        asset=MediaAsset(
            mime_type="video/mp4", provider="local-http", bytes_data=b"raw"
        ),
        start=0.0,
        end=1.0,
    )
    normalized = await normalize_operation_assets(
        op, storage=None, path_prefix="video/processed/in/"
    )
    assert normalized is op


@pytest.mark.asyncio
async def test_normalize_operation_assets_passthrough_for_uri_only() -> None:
    fake_store = AsyncMock()
    op = Trim(
        asset=MediaAsset(
            mime_type="video/mp4", provider="local-http", uri="already-there.mp4"
        ),
        start=0.0,
        end=1.0,
    )
    normalized = await normalize_operation_assets(
        op, storage=fake_store, path_prefix="video/processed/in/"
    )
    assert normalized is op
    fake_store.upload.assert_not_called()


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
