import io

import numpy as np
import pytest
import soundfile as sf

from lexigram.contracts.multimedia.types import BeatAnalysisRequest, MediaAsset
from lexigram.multimedia.beat.providers.librosa import LibrosaBeatAnalysisProvider


def _click_track_wav_bytes(
    bpm: float = 120.0, duration_s: float = 8.0, sr: int = 22050
) -> bytes:
    """Generates a WAV click track: a short burst of noise at each beat."""
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
