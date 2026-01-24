import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from lexigram.contracts.multimedia.types import (
    ComposeAudioLayer,
    ComposeLayer,
    ComposeVideo,
    MediaAsset,
    Trim,
)
from lexigram.multimedia.video.config import VideoProcessingConfig
from lexigram.multimedia.video.exceptions import VideoProcessingError
from lexigram.multimedia.video.processing.ffmpeg import FFmpegVideoProcessor

ASSET = MediaAsset(mime_type="video/mp4", provider="local-http", bytes_data=b"fake")


def _fake_proc() -> AsyncMock:
    proc = AsyncMock()
    proc.communicate.return_value = (b"", b"")
    proc.returncode = 0
    return proc


def _exec_writing_output(captured: list[list[str]]) -> AsyncMock:
    proc = _fake_proc()

    async def fake_exec(*args, **kwargs):
        argv = list(args)
        captured.append(argv)
        with open(argv[-1], "wb") as f:
            f.write(b"rendered")
        return proc

    return fake_exec


def _make_stream(*lines: bytes) -> asyncio.StreamReader:
    stream = asyncio.StreamReader()
    for line in lines:
        stream.feed_data(line)
    stream.feed_eof()
    return stream


class _FakeProc:
    def __init__(
        self,
        stdout: asyncio.StreamReader,
        stderr: asyncio.StreamReader,
        *,
        exited: bool = True,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = 0
        self.killed = False
        self._exited = exited

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        if self.killed or self._exited:
            return self.returncode
        await asyncio.sleep(10)
        return self.returncode


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


@pytest.mark.asyncio
async def test_compose_materializes_base_layers_audio_in_order(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)
    base = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=b"base")
    layer = MediaAsset(mime_type="video/quicktime", provider="test", bytes_data=b"layer")
    audio = MediaAsset(mime_type="audio/wav", provider="test", bytes_data=b"audio")
    op = ComposeVideo(
        asset=base,
        layers=[ComposeLayer(asset=layer, start=1.0)],
        audio_layers=[ComposeAudioLayer(asset=audio, start=2.0)],
    )

    captured: list[list[str]] = []
    input_bytes: list[bytes] = []

    async def fake_exec(*args, **kwargs):
        argv = list(args)
        captured.append(argv)
        assert argv[0] == "ffmpeg"
        input_bytes[:] = [
            Path(argv[i + 1]).read_bytes() for i, arg in enumerate(argv) if arg == "-i"
        ]
        with open(argv[-1], "wb") as f:
            f.write(b"rendered")
        return _fake_proc()

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        result = await processor.process(op)

    assert result.is_ok()
    assert result.unwrap().provider == "ffmpeg"
    assert result.unwrap().bytes_data == b"rendered"
    assert input_bytes == [b"base", b"layer", b"audio"]


@pytest.mark.asyncio
async def test_compose_probes_durations_and_builds_fades(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)
    base = MediaAsset(mime_type="video/mp4", provider="test", bytes_data=b"base")
    layer = MediaAsset(mime_type="video/quicktime", provider="test", bytes_data=b"layer")
    op = ComposeVideo(
        asset=base,
        layers=[ComposeLayer(asset=layer, start=1.0, fade_out=0.3)],
        fade_out=0.5,
        base_fade_out=0.75,
    )

    captured: list[list[str]] = []

    async def fake_exec(*args, **kwargs):
        argv = list(args)
        captured.append(argv)
        with open(argv[-1], "wb") as f:
            f.write(b"rendered")
        return _fake_proc()

    with (
        patch(
            "lexigram.multimedia.video.processing.ffmpeg.probe_duration",
            AsyncMock(side_effect=[30.0, 3.0]),
        ),
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
    ):
        result = await processor.process(op)

    assert result.is_ok()
    argv = captured[0]
    fc = argv[argv.index("-filter_complex") + 1]
    assert "[0:v]fade=t=out:st=29.25:d=0.75[b0]" in fc
    assert "fade=t=out:st=2.7:d=0.3[l0]" in fc
    assert "[v0]fade=t=out:st=29.5:d=0.5[v]" in fc


@pytest.mark.asyncio
async def test_progress_callback_streams_out_time(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path))
    processor = FFmpegVideoProcessor(config=config)

    out_lines = [
        b"out_time_us=500000\n",
        b"out_time_us=1500000\n",
        b"out_time_us=9500000\n",
        b"progress=end\n",
    ]
    stderr = _make_stream(b"")
    stdout = _make_stream(*out_lines)
    seen: list[float] = []
    captured: list[list[str]] = []

    async def fake_exec(*args, **kwargs):
        argv = list(args)
        captured.append(argv)
        with open(argv[-1], "wb") as f:
            f.write(b"rendered")
        return _FakeProc(stdout, stderr)

    with (
        patch(
            "lexigram.multimedia.video.processing.ffmpeg.probe_duration",
            AsyncMock(return_value=10.0),
        ),
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
    ):
        result = await processor.process(
            Trim(asset=ASSET, start=0.0, end=1.0), progress_callback=seen.append
        )

    assert result.is_ok()
    assert seen == [0.05, 0.15, 0.95, 1.0]
    argv = captured[0]
    assert "-nostats" in argv
    assert "-progress" in argv


@pytest.mark.asyncio
async def test_progress_timeout_kills_process(tmp_path):
    config = VideoProcessingConfig(temp_dir=str(tmp_path), timeout=0.05)
    processor = FFmpegVideoProcessor(config=config)

    stdout = asyncio.StreamReader()
    stderr = _make_stream(b"")
    proc = _FakeProc(stdout, stderr, exited=False)
    captured: list[list[str]] = []

    async def fake_exec(*args, **kwargs):
        argv = list(args)
        captured.append(argv)
        return proc

    with (
        patch(
            "lexigram.multimedia.video.processing.ffmpeg.probe_duration",
            AsyncMock(return_value=10.0),
        ),
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
    ):
        result = await processor.process(
            Trim(asset=ASSET, start=0.0, end=1.0), progress_callback=lambda p: None
        )

    assert result.is_err()
    assert isinstance(result.unwrap_err(), VideoProcessingError)
    assert proc.killed
