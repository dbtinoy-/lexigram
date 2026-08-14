# lexigram-multimedia-music

Music generation for the Lexigram Framework — local and API-based backends (`local-http`, `stability-audio`, `ace-step`, `stable-audio-open`).

---

## Overview

`lexigram-multimedia-music` generates music and sound from a text prompt. The default backend calls a local HTTP reference server (`http://localhost:5003`) so the package works out of the box with no API keys; hosted backends (Stability Audio) and in-process reference servers (ACE-Step, Stable Audio Open) are selectable via config.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-multimedia-music
# Optional extras
uv add "lexigram-multimedia-music[stability-audio]"    # Stability Audio API
uv add "lexigram-multimedia-music[ace-step-server]"    # local ACE-Step server (torch)
uv add "lexigram-multimedia-music[stable-audio-open-server]"  # local Stable Audio Open server (torch)
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.music import AudioMusicModule
from lexigram.contracts.multimedia import MusicProvider, MusicRequest


@module(imports=[AudioMusicModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        music = await app.container.resolve(MusicProvider)
        result = await music.generate(MusicRequest(prompt="upbeat synthwave, 120 bpm"))
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — audio bytes or URI


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `AudioMusicModule.configure()` with no arguments to use the `local-http` backend at `http://localhost:5003`.

### Option 1 — YAML file

```yaml
# application.yaml
multimedia:
  music:
    backend: "ace-step"
```

### Option 2 — Profiles + Environment Variables

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA_MUSIC__BACKEND=ace-step
```

### Option 3 — Python

```python
from lexigram.multimedia.music import AudioMusicModule
from lexigram.multimedia.music.config import MusicConfig

AudioMusicModule.configure(config=MusicConfig(backend="ace-step"))
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend` | `"local-http"` | `LEX_MULTIMEDIA_MUSIC__BACKEND` | `local-http`, `stability-audio`, `ace-step`, `stable-audio-open` |
| `local_http_base_url` | `"http://localhost:5003"` | `LEX_MULTIMEDIA_MUSIC__LOCAL_HTTP_BASE_URL` | Local reference server URL |
| `ace_step_base_url` | `"http://localhost:5300"` | `LEX_MULTIMEDIA_MUSIC__ACE_STEP_BASE_URL` | ACE-Step server URL |
| `stable_audio_open_base_url` | `"http://localhost:5301"` | `LEX_MULTIMEDIA_MUSIC__STABLE_AUDIO_OPEN_BASE_URL` | Stable Audio Open server URL |
| `timeout` | `60.0` | `LEX_MULTIMEDIA_MUSIC__TIMEOUT` | Request timeout in seconds |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AudioMusicModule.configure(config)` | Configure with explicit music config |
| `AudioMusicModule.stub()` | Real module pinned to the default `local-http` backend for tests |

## Key Features

- **Four backends** — `local-http`, `stability-audio`, `ace-step`, `stable-audio-open`
- **Reference servers** — `lexigram-music-ace-step-serve` and `lexigram-music-stable-audio-open-serve` console scripts run each local model server
- **Result-based** — `generate() -> Result[MediaAsset, MultimediaError]`; errors are domain values, not exceptions

## Testing

```python
from lexigram import Application
from lexigram.multimedia.music import AudioMusicModule


async def test_boot():
    async with Application.boot(modules=[AudioMusicModule.stub()]) as app:
        assert app.container is not None
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/multimedia/music/module.py` | `AudioMusicModule.configure()` and `.stub()` |
| `src/lexigram/multimedia/music/config.py` | `MusicConfig` |
| `src/lexigram/multimedia/music/di/provider.py` | `AudioMusicProvider` — registers `MusicProvider`, wires task handlers |
| `src/lexigram/multimedia/music/providers/` | Backend implementations (`local_http`, `stability_audio`, `ace_step`, `stable_audio_open`) |
| `src/lexigram/multimedia/music/servers/` | Reference-server entry points (`lexigram-music-*-serve`) |
| `src/lexigram/multimedia/music/tasks.py` | Background generation task handlers |
| `src/lexigram/multimedia/music/exceptions.py` | `MusicGenerationError` hierarchy |
