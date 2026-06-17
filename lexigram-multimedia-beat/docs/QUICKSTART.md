# Quickstart

Get tempo and beat timestamps from an audio clip in minutes.

---

## Install

```bash
uv add lexigram-multimedia-beat
```

Optional extras:

```bash
uv add "lexigram-multimedia-beat[librosa]"        # librosa in-process backend
uv add "lexigram-multimedia-beat[madmom-server]"  # madmom reference server (DL-based)
```

The base dependency set (`aiohttp`, `lexigram`, `lexigram-contracts`) is enough to boot
the module; the backend you actually run under needs its extra.

---

## Basic Usage

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia.protocols import BeatAnalysisProvider
from lexigram.contracts.multimedia.types import BeatAnalysisRequest, MediaAsset
from lexigram.multimedia.beat import BeatAnalysisModule


async def main() -> None:
    app = Application(name="beat-demo")
    app.add_module(BeatAnalysisModule.configure())  # default: in-process librosa
    await app.start()

    beat = await app.container.resolve(BeatAnalysisProvider)
    asset = MediaAsset(
        mime_type="audio/mp3",
        provider="local",
        bytes_data=b"\x00\xff\xf1...",  # real audio bytes in practice
    )
    result = await beat.analyze(BeatAnalysisRequest(asset=asset))
    if result.is_ok():
        analysis = result.unwrap()  # BeatAnalysisResult
        print(f"tempo: {analysis.tempo_bpm} bpm")
        print(f"beats: {analysis.beat_timestamps}")

    await app.stop()


asyncio.run(main())
```

---

## What Just Happened

1. `BeatAnalysisModule.configure()` returns a `DynamicModule` with one
   `BeatAnalysisGenerationProvider` and exports `BeatAnalysisProvider`.
2. During `app.start()`, the provider's `register()` reads `BeatAnalysisConfig`
   (default `backend="librosa"`), constructs a `LibrosaBeatAnalysisProvider` with the
   configured `librosa_sample_rate`, and binds it as the `BeatAnalysisProvider` singleton.
3. `container.resolve(BeatAnalysisProvider)` returns that backend. `analyze()` materializes
   the asset bytes to a temp file, runs librosa's beat tracker (`librosa.beat.beat_track`)
   off the event loop (`asyncio.to_thread`), and returns
   `Result[BeatAnalysisResult, MultimediaError]`.
4. The result is a plain value — `tempo_bpm` plus `beat_timestamps` — nothing is persisted
   to storage and no job is queued. That's by design: there is no blob to store.

---

## Next Steps

- [Guide](./GUIDE.md) — the two backends, when to use which, integration with the umbrella
- [How-Tos](./HOWTOS.md) — madmom server setup, beat-synced cutting, resilience recipes
- [Configuration](./CONFIGURATION.md) — `multimedia_beat:` config and env vars
- [Architecture](./ARCHITECTURE.md) — provider wiring and the server protocol