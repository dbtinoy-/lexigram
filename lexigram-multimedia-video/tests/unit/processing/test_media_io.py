import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.video.processing.media_io import (
    materialize_asset,
    probe_duration,
    read_output_asset,
)


@pytest.mark.asyncio
async def test_materialize_asset_writes_bytes_to_tempfile(tmp_path):
    asset = MediaAsset(
        mime_type="video/mp4", provider="local-http", bytes_data=b"fake-mp4-bytes"
    )
    path = await materialize_asset(asset, temp_dir=str(tmp_path))
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read() == b"fake-mp4-bytes"


@pytest.mark.asyncio
async def test_materialize_asset_downloads_uri(tmp_path):
    asset = MediaAsset(
        mime_type="video/mp4",
        provider="local-http",
        uri="https://cdn.example/a.mp4",
    )
    fake_resp = AsyncMock()
    fake_resp.read.return_value = b"downloaded-bytes"
    fake_resp.status = 200
    fake_session = MagicMock()
    fake_session.get.return_value.__aenter__.return_value = fake_resp
    with patch("aiohttp.ClientSession") as mock_session_cls:
        mock_session_cls.return_value.__aenter__.return_value = fake_session
        path = await materialize_asset(asset, temp_dir=str(tmp_path))
    with open(path, "rb") as f:
        assert f.read() == b"downloaded-bytes"


def test_read_output_asset_reads_bytes(tmp_path):
    out_path = tmp_path / "out.mp4"
    out_path.write_bytes(b"result-bytes")
    asset = read_output_asset(str(out_path), mime_type="video/mp4", provider="ffmpeg")
    assert asset.bytes_data == b"result-bytes"
    assert asset.mime_type == "video/mp4"
    assert asset.provider == "ffmpeg"


@pytest.mark.asyncio
async def test_probe_duration_parses_ffprobe_output():
    fake_proc = AsyncMock()
    fake_proc.communicate.return_value = (b"12.345\n", b"")
    fake_proc.returncode = 0
    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        duration = await probe_duration("/tmp/whatever.mp4", ffprobe_binary="ffprobe")
    assert duration == pytest.approx(12.345)
