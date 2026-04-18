"""Materialize MediaAssets to local disk for ffmpeg, and read results back."""

from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
from urllib.parse import unquote, urlparse
import uuid

import aiohttp

from lexigram.contracts.multimedia.types import MediaAsset


async def materialize_asset(asset: MediaAsset, *, temp_dir: str | None = None) -> str:
    """Write an asset's bytes to a local temp file, downloading first if it's a URI.

    Returns the local filesystem path ffmpeg can read.
    """
    if asset.has_bytes:
        suffix = _suffix_from_mime(asset.mime_type)
        path = f"{tempfile.gettempdir() if temp_dir is None else temp_dir}/{uuid.uuid4().hex}{suffix}"
        with open(path, "wb") as f:
            f.write(asset.bytes_data or b"")
        return path

    if asset.uri is not None and asset.uri.startswith("file://"):
        path = unquote(urlparse(asset.uri).path)
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        return path

    suffix = _suffix_from_mime(asset.mime_type)
    path = f"{tempfile.gettempdir() if temp_dir is None else temp_dir}/{uuid.uuid4().hex}{suffix}"
    async with (
        aiohttp.ClientSession() as session,
        session.get(asset.uri) as resp,  # type: ignore[arg-type]
    ):
        body = await resp.read()
    with open(path, "wb") as f:
        f.write(body)
    return path


def read_output_asset(path: str, *, mime_type: str, provider: str) -> MediaAsset:
    """Read an ffmpeg output file from disk into a MediaAsset."""
    with open(path, "rb") as f:
        data = f.read()
    return MediaAsset(mime_type=mime_type, provider=provider, bytes_data=data)


async def probe_duration(path: str, *, ffprobe_binary: str = "ffprobe") -> float:
    """Return a media file's duration in seconds via ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return float(stdout.decode().strip())


def _suffix_from_mime(mime_type: str) -> str:
    return {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
    }.get(mime_type, "")


__all__ = ["materialize_asset", "probe_duration", "read_output_asset"]
