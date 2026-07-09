"""In-process librosa beat/tempo-detection backend.

No reference server, no HTTP client, no torch dependency — librosa's
classical beat tracker is CPU-bound numpy/scipy code, not a deep-learning
model, so it needs no GPU and has negligible cold-start cost (design
spec §4.1). Runs directly inside whatever process constructs it.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import tempfile

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.contracts.multimedia.security import (
    DEFAULT_MAX_MEDIA_BYTES,
    asset_bytes_ok,
)
from lexigram.contracts.multimedia.types import (
    BeatAnalysisRequest,
    BeatAnalysisResult,
    MediaAsset,
)
from lexigram.contracts.security.url_safety import (
    HostResolver,
    is_safe_url_for_request,
)
from lexigram.multimedia.beat.exceptions import BeatAnalysisDecodeError


class LibrosaBeatAnalysisProvider:
    """Talks to no server — runs librosa's beat tracker in-process."""

    def __init__(
        self,
        sample_rate: int = 22050,
        max_asset_bytes: int = DEFAULT_MAX_MEDIA_BYTES,
        max_analyze_samples: int = 60_000_000,
        resolver: HostResolver | None = None,
    ) -> None:
        """
        Configure the in-process librosa backend.

        Args:
            sample_rate: Target sample rate for analysis.
            max_asset_bytes: Reject assets larger than this many bytes.
            max_analyze_samples: Reject decoded audio longer than this
                many samples.
            resolver: Optional hostname resolver for the URL-safety
                check. Defaults to the system resolver.
        """
        self._sample_rate = sample_rate
        self._max_asset_bytes = max_asset_bytes
        self._max_analyze_samples = max_analyze_samples
        self._resolver = resolver

    async def _materialize(self, asset: MediaAsset) -> str:
        """Write an asset's bytes to a temp file, enforcing size and URL policy.

        Inline bytes are rejected when they exceed ``max_asset_bytes``.
        Remote URIs are validated against the SSRF primitive and streamed
        with a hard byte cap; redirects are never followed.

        Args:
            asset: Source media asset (inline bytes or remote URI).

        Returns:
            Path to the materialized temp file.

        Raises:
            BeatAnalysisDecodeError: If the URI is unsafe, or the payload
                exceeds ``max_asset_bytes``.
        """
        fd, path = tempfile.mkstemp(suffix=".audio")
        os.close(fd)
        try:
            if asset.has_bytes:
                data = asset.bytes_data
                if not asset_bytes_ok(
                    len(data or b""), max_bytes=self._max_asset_bytes
                ):
                    raise BeatAnalysisDecodeError(
                        f"asset exceeds {self._max_asset_bytes} byte cap"
                    )
                with open(path, "wb") as f:
                    f.write(data or b"")
            else:
                uri = asset.uri
                if not uri or not is_safe_url_for_request(uri, resolver=self._resolver):
                    raise BeatAnalysisDecodeError(
                        f"unsafe or invalid asset URI: {uri!r}"
                    )
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(uri, allow_redirects=False) as resp,
                ):
                    declared = resp.content_length
                    if declared is not None and not asset_bytes_ok(
                        declared, max_bytes=self._max_asset_bytes
                    ):
                        raise BeatAnalysisDecodeError(
                            f"asset exceeds {self._max_asset_bytes} byte cap"
                        )
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        total += len(chunk)
                        if not asset_bytes_ok(total, max_bytes=self._max_asset_bytes):
                            raise BeatAnalysisDecodeError(
                                f"asset exceeds {self._max_asset_bytes} byte cap"
                            )
                        chunks.append(chunk)
                with open(path, "wb") as f:
                    f.write(b"".join(chunks))
            return path
        except BaseException:
            Path(path).unlink(missing_ok=True)
            raise

    async def analyze(
        self, request: BeatAnalysisRequest
    ) -> Result[BeatAnalysisResult, MultimediaError]:
        """Analyze an asset and return its tempo and beat timestamps.

        Args:
            request: The asset to analyze.

        Returns:
            Ok(analysis) on success, Err(error) when the asset is unsafe,
            oversized, or undecodable.
        """
        try:
            path = await self._materialize(request.asset)
        except BeatAnalysisDecodeError as exc:
            return Err(exc)
        try:
            return await asyncio.to_thread(self._analyze_sync, path)
        finally:
            Path(path).unlink()

    def _analyze_sync(self, path: str) -> Result[BeatAnalysisResult, MultimediaError]:
        """Run librosa beat tracking on a materialized audio file.

        Args:
            path: Path to the materialized audio file.

        Returns:
            Ok(analysis) on success, Err(error) when the file is
            oversized or undecodable, or the decoded array exceeds
            ``max_analyze_samples``.
        """
        if Path(path).stat().st_size > self._max_asset_bytes:
            return Err(
                BeatAnalysisDecodeError(
                    f"audio file exceeds {self._max_asset_bytes} byte cap"
                )
            )

        try:
            import librosa  # type: ignore[import-not-found]

            y, sr = librosa.load(path, sr=self._sample_rate)
        except Exception as exc:
            return Err(
                BeatAnalysisDecodeError(f"librosa could not decode audio: {exc}")
            )

        if y.size > self._max_analyze_samples:
            return Err(
                BeatAnalysisDecodeError(
                    f"decoded audio exceeds {self._max_analyze_samples} sample cap"
                )
            )

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_timestamps = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        tempo_bpm = float(tempo) if not hasattr(tempo, "item") else float(tempo.item())
        return Ok(
            BeatAnalysisResult(tempo_bpm=tempo_bpm, beat_timestamps=beat_timestamps)
        )


__all__ = ["LibrosaBeatAnalysisProvider"]
