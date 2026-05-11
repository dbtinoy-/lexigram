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
from lexigram.contracts.multimedia.types import BeatAnalysisRequest, BeatAnalysisResult
from lexigram.multimedia.beat.exceptions import BeatAnalysisDecodeError


class LibrosaBeatAnalysisProvider:
    """Talks to no server — runs librosa's beat tracker in-process."""

    def __init__(self, sample_rate: int = 22050) -> None:
        self._sample_rate = sample_rate

    async def _materialize(self, asset: object) -> str:
        fd, path = tempfile.mkstemp(suffix=".audio")
        os.close(fd)
        if asset.has_bytes:  # type: ignore[attr-defined]
            with open(path, "wb") as f:
                f.write(asset.bytes_data)  # type: ignore[attr-defined]
        else:
            async with (
                aiohttp.ClientSession() as session,
                session.get(asset.uri) as resp,  # type: ignore[attr-defined]
            ):
                data = await resp.read()
            with open(path, "wb") as f:
                f.write(data)
        return path

    async def analyze(
        self, request: BeatAnalysisRequest
    ) -> Result[BeatAnalysisResult, MultimediaError]:
        path = await self._materialize(request.asset)
        try:
            return await asyncio.to_thread(self._analyze_sync, path)
        finally:
            Path(path).unlink()

    def _analyze_sync(self, path: str) -> Result[BeatAnalysisResult, MultimediaError]:
        import librosa  # type: ignore[import-not-found]

        try:
            y, sr = librosa.load(path, sr=self._sample_rate)
        except Exception as exc:
            return Err(
                BeatAnalysisDecodeError(f"librosa could not decode audio: {exc}")
            )

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_timestamps = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        tempo_bpm = float(tempo) if not hasattr(tempo, "item") else float(tempo.item())
        return Ok(
            BeatAnalysisResult(tempo_bpm=tempo_bpm, beat_timestamps=beat_timestamps)
        )


__all__ = ["LibrosaBeatAnalysisProvider"]
