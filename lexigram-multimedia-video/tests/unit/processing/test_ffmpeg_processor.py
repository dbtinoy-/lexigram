from unittest.mock import AsyncMock, patch

import pytest

from lexigram.contracts.multimedia.types import MediaAsset, Trim
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.exceptions import VideoProcessingError
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor

ASSET = MediaAsset(mime_type="video/mp4", provider="local-http", bytes_data=b"fake")


@pytest.mark.asyncio
async def test_process_trim_success(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    fake_proc = AsyncMock()
    fake_proc.communicate.return_value = (b"", b"")
    fake_proc.returncode = 0

    async def fake_exec(*args, **kwargs):
        # Simulate ffmpeg writing the output file.
        output_path = args[-1]
        with open(output_path, "wb") as f:
            f.write(b"trimmed-bytes")
        return fake_proc

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        result = await processor.process(Trim(asset=ASSET, start=0.0, end=1.0))

    assert result.is_ok()
    asset = result.unwrap()
    assert asset.bytes_data == b"trimmed-bytes"
    assert asset.provider == "ffmpeg"


@pytest.mark.asyncio
async def test_process_returns_err_on_nonzero_exit(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    fake_proc = AsyncMock()
    fake_proc.communicate.return_value = (b"", b"ffmpeg error: invalid input")
    fake_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        result = await processor.process(Trim(asset=ASSET, start=0.0, end=1.0))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoProcessingError)
    assert "ffmpeg error" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_process_returns_err_on_timeout(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path), timeout=0.01)
    processor = FFmpegVideoProcessor(config=config)

    async def hang_forever(*args, **kwargs):
        import asyncio as _asyncio

        await _asyncio.sleep(10)

    fake_proc = AsyncMock()
    fake_proc.communicate.side_effect = hang_forever
    fake_proc.kill = lambda: None
    fake_proc.wait = AsyncMock()

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        result = await processor.process(Trim(asset=ASSET, start=0.0, end=1.0))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoProcessingError)


@pytest.mark.asyncio
async def test_concurrent_jobs_bounded_by_semaphore(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path), max_concurrent_jobs=1)
    processor = FFmpegVideoProcessor(config=config)
    assert processor._semaphore._value == 1
