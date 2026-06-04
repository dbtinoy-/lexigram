"""Tests for the in-process librosa beat-analysis provider.

The decode-cap tests inject a minimal fake ``librosa`` module because
``librosa``/``soundfile`` are optional extras not installed in the dev
venv (the ``_click_track_wav_bytes`` helper skips when soundfile is
absent, preserving pre-existing behavior). The guards under test — real
temp file on disk, ``Path.stat()`` size check, decoded-array ceiling —
are never faked.
"""

from __future__ import annotations

import io
import ipaddress
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import numpy as np
import pytest

from lexigram.contracts.multimedia.types import (
    BeatAnalysisRequest,
    MediaAsset,
)
from lexigram.contracts.security.url_safety import HostResolver
from lexigram.multimedia.beat.exceptions import BeatAnalysisDecodeError
from lexigram.multimedia.beat.providers.librosa import (
    LibrosaBeatAnalysisProvider,
)

pytestmark = pytest.mark.integration

_PUBLIC_IP = ipaddress.IPv4Address("93.184.216.34")


def _click_track_wav_bytes(
    bpm: float = 120.0, duration_s: float = 8.0, sr: int = 22050
) -> bytes:
    """Generates a WAV click track: a short burst of noise at each beat."""
    sf = pytest.importorskip("soundfile")
    beat_interval = 60.0 / bpm
    n_samples = int(duration_s * sr)
    audio = np.zeros(n_samples, dtype=np.float32)
    click_len = int(0.02 * sr)
    t = 0.0
    rng = np.random.default_rng(seed=42)
    while t < duration_s:
        start = int(t * sr)
        end = min(start + click_len, n_samples)
        audio[start:end] = rng.uniform(-1.0, 1.0, end - start)
        t += beat_interval
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


def _fake_librosa(n_samples: int = 100) -> ModuleType:
    """Minimal librosa stand-in that decodes to ``n_samples`` samples."""
    fake = ModuleType("librosa", "fake librosa for decode-cap tests")
    fake.load = MagicMock(return_value=(np.zeros(n_samples), 22050))
    fake.beat_track = MagicMock(return_value=(np.float64(120.0), np.array([0])))
    fake.frames_to_time = MagicMock(return_value=np.array([0.0]))
    return fake


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("uri", "resolver"),
    [
        ("http://169.254.169.254/latest/meta-data/", lambda _addr: [_PUBLIC_IP]),
        ("http://attacker.invalid/audio.wav", lambda _addr: []),
    ],
)
async def test_materialize_rejects_unresolvable_or_private_uri(
    uri: str, resolver: HostResolver
) -> None:
    provider = LibrosaBeatAnalysisProvider(resolver=resolver)
    asset = MediaAsset(mime_type="audio/wav", provider="test", uri=uri)

    with patch(
        "aiohttp.ClientSession.get",
        AsyncMock(side_effect=AssertionError("fetch attempted")),
    ):
        result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), BeatAnalysisDecodeError)


@pytest.mark.asyncio
async def test_analyze_rejects_fetched_payload_over_cap() -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(
            body=b"\0" * (25 * 1024 * 1024 + 1), content_type="audio/wav"
        )

    app = web.Application()
    app.router.add_get("/big.wav", handler)
    async with TestClient(
        TestServer(app, host="localhost"), raise_for_status=False
    ) as client:
        provider = LibrosaBeatAnalysisProvider(resolver=lambda _addr: [_PUBLIC_IP])
        asset = MediaAsset(
            mime_type="audio/wav",
            provider="test",
            uri=str(client.make_url("/big.wav")),
        )

        with patch.dict(sys.modules, {"librosa": _fake_librosa()}):
            result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), BeatAnalysisDecodeError)


@pytest.mark.asyncio
async def test_analyze_rejects_streamed_payload_over_cap() -> None:
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
        provider = LibrosaBeatAnalysisProvider(resolver=lambda _addr: [_PUBLIC_IP])
        asset = MediaAsset(
            mime_type="audio/wav",
            provider="test",
            uri=str(client.make_url("/big.bin")),
        )

        with patch.dict(sys.modules, {"librosa": _fake_librosa()}):
            result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), BeatAnalysisDecodeError)


@pytest.mark.asyncio
async def test_analyze_rejects_inline_payload_over_cap() -> None:
    provider = LibrosaBeatAnalysisProvider(max_asset_bytes=1024)
    asset = MediaAsset(
        mime_type="audio/wav", provider="test", bytes_data=b"\0" * 2048
    )

    with patch.dict(sys.modules, {"librosa": _fake_librosa()}):
        result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), BeatAnalysisDecodeError)


def test_analyze_sync_rejects_oversized_decoded_array(tmp_path: Path) -> None:
    wav_path = tmp_path / "long.wav"
    wav_path.write_bytes(b"x" * 1024)

    provider = LibrosaBeatAnalysisProvider(max_analyze_samples=1_000)
    with patch.dict(sys.modules, {"librosa": _fake_librosa(n_samples=100_000)}):
        result = provider._analyze_sync(str(wav_path))

    assert result.is_err()
    assert isinstance(result.unwrap_err(), BeatAnalysisDecodeError)


@pytest.mark.asyncio
async def test_analyze_detects_tempo_within_tolerance() -> None:
    provider = LibrosaBeatAnalysisProvider()
    wav_bytes = _click_track_wav_bytes(bpm=120.0)
    asset = MediaAsset(mime_type="audio/wav", provider="test", bytes_data=wav_bytes)

    result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_ok()
    analysis = result.unwrap()
    assert abs(analysis.tempo_bpm - 120.0) < 15.0
    assert len(analysis.beat_timestamps) > 1
    assert all(
        b2 > b1
        for b1, b2 in zip(
            analysis.beat_timestamps, analysis.beat_timestamps[1:], strict=False
        )
    )


@pytest.mark.asyncio
async def test_analyze_returns_err_on_undecodable_asset() -> None:
    provider = LibrosaBeatAnalysisProvider()
    asset = MediaAsset(
        mime_type="audio/wav", provider="test", bytes_data=b"not-real-audio"
    )

    result = await provider.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_err()
