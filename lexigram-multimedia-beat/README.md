# lexigram-multimedia-beat

Audio tempo/beat analysis for the Lexigram Framework — analyzes an audio `MediaAsset` and returns tempo (BPM) and beat timestamps for driving beat-synced cut timing.

---

## Overview

`lexigram-multimedia-beat` analyzes an audio clip and returns a `BeatAnalysisResult` (`tempo_bpm` + `beat_timestamps`). Two backends are available: `librosa` (default, runs in-process, no reference server) and `madmom` (optional, deep-learning-based, reference-server pattern — better on syncopated or tempo-changing material).

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-multimedia-beat
# Optional extras
uv add "lexigram-multimedia-beat[librosa]"        # librosa in-process backend
uv add "lexigram-multimedia-beat[madmom-server]"  # madmom reference server
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.beat import BeatAnalysisModule
from lexigram.contracts.multimedia.protocols import BeatAnalysisProvider
from lexigram.contracts.multimedia.types import BeatAnalysisRequest, MediaAsset


@module(imports=[BeatAnalysisModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        beat = await app.container.resolve(BeatAnalysisProvider)
        asset = MediaAsset(mime_type="audio/mp3", provider="local", bytes_data=b"<mp3>")
        result = await beat.analyze(BeatAnalysisRequest(asset=asset))
        if result.is_ok():
            analysis = (
                result.unwrap()
            )  # BeatAnalysisResult — tempo_bpm + beat_timestamps
            print(analysis.tempo_bpm)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `BeatAnalysisModule.configure()` with no arguments to use the in-process `librosa` backend.

### Option 1 — YAML file

```yaml
# application.yaml
multimedia_beat:
  backend: "librosa"
  librosa_sample_rate: 44100
```

### Option 2 — Profiles + Environment Variables

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA_BEAT__BACKEND=madmom
export LEX_MULTIMEDIA_BEAT__LIBROSA_SAMPLE_RATE=44100
```

### Option 3 — Python

```python
from lexigram.multimedia.beat import BeatAnalysisModule
from lexigram.multimedia.beat.config import BeatAnalysisConfig

BeatAnalysisModule.configure(
    config=BeatAnalysisConfig(backend="librosa", librosa_sample_rate=44100)
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend` | `"librosa"` | `LEX_MULTIMEDIA_BEAT__BACKEND` | `librosa` (in-process), `madmom` (reference server) |
| `librosa_sample_rate` | `22050` | `LEX_MULTIMEDIA_BEAT__LIBROSA_SAMPLE_RATE` | Sample rate for the librosa backend |
| `madmom_base_url` | `"http://localhost:5600"` | `LEX_MULTIMEDIA_BEAT__MADMOM_BASE_URL` | Madmom server URL |
| `timeout` | `30.0` | `LEX_MULTIMEDIA_BEAT__TIMEOUT` | Request timeout in seconds |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `BeatAnalysisModule.configure(config)` | Configure with explicit beat-analysis config |
| `BeatAnalysisModule.stub()` | No-op module for unit testing (uses `librosa`) |

## Key Features

- **Two backends** — `librosa` (in-process, default, no reference server) and `madmom` (deep-learning, reference-server pattern)
- **No blob persistence** — returns a `BeatAnalysisResult` (tempo + beat timestamps), not a `MediaAsset`; no queued task handler
- **Beat-synced editing** — drive cut timing in the calling application
- **Reference server** — `lexigram-beat-madmom-serve` console script runs the madmom model server
- **Result-based** — `analyze() -> Result[BeatAnalysisResult, MultimediaError]`; errors are domain values, not exceptions

## Testing

```python
from lexigram import Application
from lexigram.multimedia.beat import BeatAnalysisModule


async def test_boot():
    async with Application.boot(modules=[BeatAnalysisModule.stub()]) as app:
        assert app.container is not None
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/multimedia/beat/module.py` | `BeatAnalysisModule.configure()` and `.stub()` |
| `src/lexigram/multimedia/beat/config.py` | `BeatAnalysisConfig` |
| `src/lexigram/multimedia/beat/di/provider.py` | `BeatAnalysisGenerationProvider` — registers `BeatAnalysisProvider` |
| `src/lexigram/multimedia/beat/providers/` | Backend implementations (`librosa`, `madmom`) |
| `src/lexigram/multimedia/beat/servers/` | Reference-server entry point (`lexigram-beat-madmom-serve`) |
| `src/lexigram/multimedia/beat/exceptions.py` | `BeatAnalysisError` hierarchy |
