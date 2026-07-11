import ipaddress
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.video.processing.media_io import (
    materialize_asset,
    materialize_frames_sequential,
    probe_duration,
    probe_fps,
    read_output_asset,
)

_PUBLIC_IP = ipaddress.IPv4Address("93.184.216.34")

pytestmark_ffmpeg = pytest.mark.skipif(
    shutil.which("ffprobe") is None, reason="ffprobe not installed"
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
    fake_resp.status = 200
    fake_resp.content_length = len(b"downloaded-bytes")

    async def fake_chunks(chunk_size):
        yield b"downloaded-bytes"

    fake_resp.content.iter_chunked = MagicMock(side_effect=fake_chunks)
    fake_session = MagicMock()
    fake_session.get.return_value.__aenter__.return_value = fake_resp
    with patch("aiohttp.ClientSession") as mock_session_cls:
        mock_session_cls.return_value.__aenter__.return_value = fake_session
        path = await materialize_asset(
            asset, temp_dir=str(tmp_path), resolver=lambda _: [_PUBLIC_IP]
        )
    with open(path, "rb") as f:
        assert f.read() == b"downloaded-bytes"
    fake_session.get.assert_called_once_with(
        "https://cdn.example/a.mp4", allow_redirects=False
    )


@pytest.mark.asyncio
async def test_materialize_asset_rejects_oversized_uri_body(tmp_path):
    async def handler(request: web.Request) -> web.Response:
        return web.Response(
            body=b"\0" * (25 * 1024 * 1024 + 1), content_type="video/mp4"
        )

    app = web.Application()
    app.router.add_get("/big.mp4", handler)
    async with TestClient(
        TestServer(app, host="localhost"), raise_for_status=False
    ) as client:
        asset = MediaAsset(
            mime_type="video/mp4",
            provider="x",
            uri=str(client.make_url("/big.mp4")),
        )
        with pytest.raises(ValueError, match="too large"):
            await materialize_asset(
                asset, temp_dir=str(tmp_path), resolver=lambda _: [_PUBLIC_IP]
            )


@pytest.mark.asyncio
async def test_materialize_asset_rejects_streamed_uri_body_over_cap(tmp_path):
    async def handler(request: web.Request) -> web.StreamResponse:
        resp = web.StreamResponse()
        await resp.prepare(request)
        await resp.write(b"\0" * (25 * 1024 * 1024 + 1))
        await resp.write_eof()
        return resp

    app = web.Application()
    app.router.add_get("/big.bin", handler)
    async with TestClient(
        TestServer(app, host="localhost"), raise_for_status=False
    ) as client:
        asset = MediaAsset(
            mime_type="video/mp4",
            provider="x",
            uri=str(client.make_url("/big.bin")),
        )
        with pytest.raises(ValueError, match="too large"):
            await materialize_asset(
                asset, temp_dir=str(tmp_path), resolver=lambda _: [_PUBLIC_IP]
            )


@pytest.mark.asyncio
async def test_materialize_asset_rejects_private_uri(tmp_path):
    asset = MediaAsset(
        mime_type="video/mp4",
        provider="x",
        uri="http://127.0.0.1:9/x.mp4",
    )
    with patch(
        "aiohttp.ClientSession.get",
        AsyncMock(side_effect=AssertionError("fetch attempted")),
    ):
        with pytest.raises(ValueError, match="unsafe"):
            await materialize_asset(
                asset, temp_dir=str(tmp_path), resolver=lambda _: [_PUBLIC_IP]
            )


@pytest.mark.asyncio
async def test_materialize_asset_does_not_follow_redirects(tmp_path):
    hits: dict[str, int] = {"private": 0}

    async def private_handler(request: web.Request) -> web.Response:
        hits["private"] += 1
        return web.Response(body=b"private-bytes", content_type="video/mp4")

    async def redirect_handler(request: web.Request) -> web.Response:
        return web.Response(
            status=302,
            headers={"Location": str(request.url.with_path("/private.mp4"))},
        )

    app = web.Application()
    app.router.add_get("/private.mp4", private_handler)
    app.router.add_get("/start.mp4", redirect_handler)
    async with TestClient(
        TestServer(app, host="localhost"), raise_for_status=False
    ) as client:
        asset = MediaAsset(
            mime_type="video/mp4",
            provider="x",
            uri=str(client.make_url("/start.mp4")),
        )
        with pytest.raises(ValueError, match="asset download failed"):
            await materialize_asset(
                asset, temp_dir=str(tmp_path), resolver=lambda _: [_PUBLIC_IP]
            )
    assert hits["private"] == 0


@pytest.mark.asyncio
async def test_materialize_file_uri_passthrough(tmp_path):
    target = tmp_path / "clip.mov"
    target.write_bytes(b"x" * 64)
    asset = MediaAsset(
        mime_type="video/quicktime", provider="local-http", uri=f"file://{target}"
    )
    path = await materialize_asset(asset)
    assert path == str(target)


@pytest.mark.asyncio
async def test_materialize_file_uri_missing_raises():
    asset = MediaAsset(
        mime_type="video/mp4", provider="local-http", uri="file:///nonexistent/x.mp4"
    )
    with pytest.raises(FileNotFoundError):
        await materialize_asset(asset)


@pytest.mark.asyncio
async def test_materialize_bytes_win_over_file_uri(tmp_path):
    target = tmp_path / "clip.mov"
    target.write_bytes(b"on-disk")
    asset = MediaAsset(
        mime_type="video/quicktime",
        provider="local-http",
        uri=f"file://{target}",
        bytes_data=b"in-memory",
    )
    path = await materialize_asset(asset)
    assert path != str(target)
    with open(path, "rb") as f:
        assert f.read() == b"in-memory"


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


@pytest.mark.asyncio
async def test_probe_duration_times_out_and_kills_ffprobe(tmp_path) -> None:
    import time

    hang = tmp_path / "hang-ffprobe"
    hang.write_text("#!/bin/sh\nwhile :; do :; done\n")
    hang.chmod(0o755)

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await probe_duration(
            "/tmp/slow.mp4", ffprobe_binary=str(hang), timeout=0.2
        )

    assert time.monotonic() - started < 5.0


@pytestmark_ffmpeg
@pytest.mark.asyncio
async def test_probe_fps_reads_synthetic_clip_rate(tmp_path) -> None:
    import asyncio

    path = str(tmp_path / "clip.mp4")
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=24:d=1", path
    )
    await proc.wait()

    fps = await probe_fps(path)

    assert 23.0 < fps < 25.0


def test_materialize_frames_sequential_writes_numbered_files(tmp_path) -> None:
    frames = [
        MediaAsset(mime_type="image/png", provider="test", bytes_data=b"frame-a"),
        MediaAsset(mime_type="image/png", provider="test", bytes_data=b"frame-b"),
    ]

    pattern = materialize_frames_sequential(frames, temp_dir=str(tmp_path))

    assert pattern == f"{tmp_path}/frame%06d.png"
    assert (tmp_path / "frame000000.png").read_bytes() == b"frame-a"
    assert (tmp_path / "frame000001.png").read_bytes() == b"frame-b"
