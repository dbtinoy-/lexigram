# Quickstart

Get up and running with the multimedia generation umbrella in minutes.

---

## Install

```bash
uv add lexigram-multimedia
```

`lexigram-multimedia` pulls in `lexigram`, `lexigram-contracts`, and all seven sibling
extension packages (`lexigram-multimedia-tts`, `-music`, `-video`, `-image`, `-upscale`,
`-interpolate`, `-beat`) plus `lexigram-tasks` and `lexigram-storage`.

Backend features are opt-in per subsystem — install the extra for the backend you need:

```bash
uv add "lexigram-multimedia-tts[elevenlabs,openai]"
uv add "lexigram-multimedia-music[ace-step-server]"
uv add "lexigram-multimedia-video[wan22-server,cogvideox-server]"
```

With zero extras, the umbrella uses the default in-process/`local-http` backends.

---

## Basic Usage

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import TTSProvider, TTSRequest
from lexigram.multimedia import MultimediaConfig, MultimediaModule


async def main() -> None:
    config = MultimediaConfig(cache_results=False)
    app = Application(name="my-media-app")
    app.add_module(MultimediaModule.configure(config=config))

    await app.start()

    tts = await app.container.resolve(TTSProvider)
    result = await tts.generate(TTSRequest(text="Hello from Lexigram"))
    if result.is_ok():
        asset = result.unwrap()  # MediaAsset — bytes or a URI
        if asset.has_uri:
            print(f"Generated audio: {asset.uri}")

    await app.stop()


asyncio.run(main())
```

> **Note:** `MultimediaModule.configure()` with **no arguments** is zero-config — it
> constructs a default `MultimediaConfig()` internally. Use no-arg for the fastest path.

---

## What Just Happened

1. `MultimediaModule.configure()` returns a `DynamicModule` owning one `MultimediaProvider`
   and **exporting** all seven subsystem protocols (`TTSProvider`, `MusicProvider`,
   `VideoProvider`, `ImageProvider`, `UpscaleProvider`, `InterpolationProvider`,
   `BeatAnalysisProvider`).
2. On `app.start()`, `MultimediaProvider.register()` binds each sub-provider
   (`AudioTTSProvider`, `AudioMusicProvider`, `VideoGenerationProvider`,
   `ImageGenerationProvider`, `UpscaleGenerationProvider`,
   `InterpolationGenerationProvider`, `BeatAnalysisGenerationProvider`) and delegates
   to their `register()` — that is what puts `TTSProvider` into the container.
3. On `boot()`, the provider cleanly resolves optional `BlobStoreProtocol`,
   `CacheBackendProtocol`, and `EventBusProtocol` so nothing breaks when those
   subsystems are absent, then wires the task queue.
4. `container.resolve(TTSProvider)` returns the concrete TTS backend. Calling
   `generate()` returns `Result[MediaAsset, MultimediaError]` — never raises for
   expected failures.

---

## Next Steps

- [Guide](./GUIDE.md) — the accessor model, sync vs queued jobs, timeline composition
- [How-Tos](./HOWTOS.md) — TTS, music, video, upscale, interpolate, beat, compose recipes
- [Configuration](./CONFIGURATION.md) — the `multimedia:` config tree and env vars
- [Architecture](./ARCHITECTURE.md) — provider wiring and extension points