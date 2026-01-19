from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.infra.storage.models import FileInfo
from lexigram.contracts.multimedia.types import MediaAsset, Trim
from lexigram.multimedia.input_normalize import normalize_operation_assets


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
