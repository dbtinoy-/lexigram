"""Materialize MediaAssets to local disk for ffmpeg, and read results back."""

from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
from urllib.parse import unquote, urlparse
import uuid

import aiohttp

from lexigram.contracts.multimedia.security import (
    DEFAULT_MAX_MEDIA_BYTES,
    asset_bytes_ok,
)
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.contracts.security.url_safety import (
    HostResolver,
    is_safe_url_for_request,
)
from lexigram.multimedia.video.exceptions import (
    VideoAssetDownloadError,
    VideoAssetTooLargeError,
    VideoUnsafeAssetURLError,
)


async def materialize_asset(
    asset: MediaAsset,
    *,
    temp_dir: str | None = None,
    max_bytes: int = DEFAULT_MAX_MEDIA_BYTES,
    resolver: HostResolver | None = None,
) -> str:
    """Write an asset's bytes to a local temp file, downloading first if it's a URI.

    Inline bytes are written as-is; ``file://`` URIs pass through as local
    paths (the framework's internal materialization contract). Remote URIs
    are validated against the SSRF primitive (``is_safe_url_for_request``)
    and streamed with a hard byte cap; redirects are never followed and
    non-200 responses are rejected.

    Args:
        asset: Source media asset (inline bytes, ``file://`` URI, or remote
            URI).
        temp_dir: Directory for the temp file. Defaults to the system temp
            dir.
        max_bytes: Maximum accepted payload size in bytes. Defaults to the
            framework media cap.
        resolver: Optional hostname resolver for the URL-safety check.
            Defaults to the system resolver.

    Returns:
        The local filesystem path ffmpeg can read.

    Raises:
        FileNotFoundError: If a ``file://`` asset path does not exist.
        VideoAssetTooLargeError: If the remote payload exceeds
            ``max_bytes``.
        VideoUnsafeAssetURLError: If the remote URI is missing or not safe
            to request.
        VideoAssetDownloadError: If the remote fetch returns a non-200
            response.
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

    uri = asset.uri
    if not uri or not is_safe_url_for_request(uri, resolver=resolver):
        raise VideoUnsafeAssetURLError(uri or "")
    suffix = _suffix_from_mime(asset.mime_type)
    path = f"{tempfile.gettempdir() if temp_dir is None else temp_dir}/{uuid.uuid4().hex}{suffix}"
    async with (
        aiohttp.ClientSession() as session,
        session.get(uri, allow_redirects=False) as resp,
    ):
        if resp.status != 200:
            raise VideoAssetDownloadError(resp.status)
        declared = resp.content_length
        if declared is not None and not asset_bytes_ok(declared, max_bytes=max_bytes):
            raise VideoAssetTooLargeError(max_bytes)
        chunks: list[bytes] = []
        total = 0
        async for chunk in resp.content.iter_chunked(64 * 1024):
            total += len(chunk)
            if not asset_bytes_ok(total, max_bytes=max_bytes):
                raise VideoAssetTooLargeError(max_bytes)
            chunks.append(chunk)
    with open(path, "wb") as f:
        f.write(b"".join(chunks))
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


async def probe_fps(path: str, *, ffprobe_binary: str = "ffprobe") -> float:
    """Return a video file's frame rate via ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        ffprobe_binary,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    raw = stdout.decode().strip()
    num, _, den = raw.partition("/")
    return float(num) / float(den or 1)


def materialize_frames_sequential(frames: list[MediaAsset], *, temp_dir: str) -> str:
    """Write frame assets to sequentially-numbered files.

    Returns ffmpeg's `%06d`-style input pattern, satisfying `-i` for
    reassembly. `materialize_asset`'s randomly-named output doesn't fit
    ffmpeg's sequential-input requirement, hence this separate helper.
    """
    for i, frame in enumerate(frames):
        path = f"{temp_dir}/frame{i:06d}.png"
        with open(path, "wb") as f:
            f.write(frame.bytes_data or b"")
    return f"{temp_dir}/frame%06d.png"


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


__all__ = [
    "materialize_asset",
    "materialize_frames_sequential",
    "probe_duration",
    "probe_fps",
    "read_output_asset",
]
