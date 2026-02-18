# lexigram-multimedia

Multimedia generation umbrella for Lexigram Framework — TTS, music, video, image, upscale, interpolation, and beat analysis in one DI module.

---

## Overview

`lexigram-multimedia` is the **orchestration layer** for the Lexigram multimedia subsystem. It wires seven independent generation packages (`lexigram-multimedia-tts`, `lexigram-multimedia-music`, `lexigram-multimedia-video`, `lexigram-multimedia-image`, `lexigram-multimedia-upscale`, `lexigram-multimedia-interpolate`, `lexigram-multimedia-beat`) through the framework's DI container and entry-point discovery, and exposes a single `MultimediaModule` for application composition. Generated assets are normalized into blob storage (`MediaAsset` with bytes or URI), and long-running jobs are submitted to the task queue.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-multimedia
# Subsystem extras (per backend, e.g. torch-based reference servers)
uv add "lexigram-multimedia-tts[elevenlabs,openai]"
uv add "lexigram-multimedia-music[ace-step-server]"
uv add "lexigram-multimedia-video[wan22-server,cogvideox-server]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia import MultimediaModule
from lexigram.contracts.multimedia import TTSProvider, TTSRequest


@module(imports=[MultimediaModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        tts = await app.container.resolve(TTSProvider)
        result = await tts.generate(TTSRequest(text="Hello from Lexigram"))
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — bytes or URI in blob storage


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `MultimediaModule.configure()` with no arguments to use defaults. The default backend for every subsystem is a local HTTP reference server (`local-http`).

### Option 1 — YAML file

```yaml
# application.yaml
multimedia:
  tts:
    backend: "elevenlabs"
    elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM"
  music:
    backend: "stable-audio-open"
  video:
    backend: "local-http"
  storage_path_prefix: "multimedia/"
  cache_results: true
```

### Option 2 — Profiles + Environment Variables

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA__TTS__BACKEND=elevenlabs
export LEX_MULTIMEDIA__STORAGE_PATH_PREFIX=multimedia/
```

### Option 3 — Python

```python
from lexigram.multimedia import MultimediaModule, MultimediaConfig
from lexigram.multimedia.tts.config import TTSConfig

MultimediaModule.configure(
    config=MultimediaConfig(
        tts=TTSConfig(backend="elevenlabs", elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM"),
        cache_results=True,
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `tts` | `TTSConfig()` | `LEX_MULTIMEDIA__TTS__*` | TTS subsystem config |
| `music` | `MusicConfig()` | `LEX_MULTIMEDIA__MUSIC__*` | Music generation config |
| `video` | `VideoConfig()` | `LEX_MULTIMEDIA__VIDEO__*` | Video generation + processing config |
| `image` | `ImageConfig()` | `LEX_MULTIMEDIA__IMAGE__*` | Image generation config |
| `upscale` | `UpscaleConfig()` | `LEX_MULTIMEDIA__UPSCALE__*` | Image/video upscale config |
| `interpolate` | `InterpolationConfig()` | `LEX_MULTIMEDIA__INTERPOLATE__*` | Frame interpolation config |
| `beat` | `BeatAnalysisConfig()` | `LEX_MULTIMEDIA__BEAT__*` | Beat analysis config |
| `storage_path_prefix` | `"multimedia/"` | `LEX_MULTIMEDIA__STORAGE_PATH_PREFIX` | Blob storage key prefix for generated assets |
| `cache_results` | `False` | `LEX_MULTIMEDIA__CACHE_RESULTS` | Cache generation results in the cache backend |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `MultimediaModule.configure(config)` | Configure with all seven subsystems wired |
| `MultimediaModule.stub()` | Stub module for testing — discovers installed subsystem stubs via `lexigram.multimedia.modules` entry points |

## Key Features

- **One module, seven subsystems** — TTS, music, video, image, upscale, interpolation, and beat analysis wired through DI
- **Entry-point discovery** — subsystem providers register via `lexigram.multimedia.subsystems`; no manual wiring
- **`SubsystemAccessor`** — single accessor to generate any media type (`generate(request) -> Result[MediaAsset, MultimediaError]`)
- **`VideoAccessor` / `ComposeAccessor` / `BeatAccessor`** — video processing, timeline composition, and beat analysis with dedicated accessors
- **Async job submission** — `submit()` dispatches generation to the task queue with idempotency and generation events
- **Blob-backed assets** — results normalized into `MediaAsset` (bytes or URI) via `lexigram-storage`

## Testing

```python
from lexigram import Application
from lexigram.multimedia import MultimediaModule


async def test_boot():
    async with Application.boot(modules=[MultimediaModule.stub()]) as app:
        assert app.container is not None
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/multimedia/__init__.py` | Public API: `MultimediaModule`, `MultimediaProvider`, `MultimediaConfig`, accessors, `Timeline` |
| `src/lexigram/multimedia/module.py` | `MultimediaModule.configure()` and `MultimediaModule.stub()` |
| `src/lexigram/multimedia/config.py` | `MultimediaConfig` — nested subsystem configs + storage/cache options |
| `src/lexigram/multimedia/di/provider.py` | `MultimediaProvider` — registers and boots the seven sub-providers |
| `src/lexigram/multimedia/accessors/` | `SubsystemAccessor`, `VideoAccessor`, `ComposeAccessor`, `BeatAccessor` |
| `src/lexigram/multimedia/timeline/` | `Timeline`, `TimelineRenderTask` — timeline composition |
| `src/lexigram/multimedia/types.py` | `JobHandle` and accessor types |
