# Quickstart: lexigram-multimedia-music

Generate music and sound effects from a text prompt, wired through the Lexigram DI container. The default backend talks to a local HTTP reference server, so it works with **zero API keys**.

---

## Install

```bash
uv add lexigram-multimedia-music
```

Optional extras pull in a backend's model runtime for local inference:

```bash
uv add "lexigram-multimedia-music[ace-step-server]"          # local ACE-Step full-song server (torch)
uv add "lexigram-multimedia-music[stable-audio-open-server]" # local Stable Audio Open FX server (torch)
```

> `lexigram-multimedia-music` depends on `lexigram` and `lexigram-contracts` (installed automatically). `aiohttp` is a hard dependency used by every backend.

---

## Minimal Working Example

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import MusicProvider, MusicRequest
from lexigram.di.module import Module, module
from lexigram.multimedia.music import AudioMusicModule


@module(imports=[AudioMusicModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        music = await app.container.resolve(MusicProvider)
        result = await music.generate(MusicRequest(prompt="upbeat synthwave, 120 bpm"))
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — raw WAV/MP3 bytes
            print(asset.mime_type, asset.has_bytes)


asyncio.run(main())
```

Run a local music server in a separate terminal first (any of the `*-serve` scripts), or point the config at an already-running host:

```bash
lexigram-music-stable-audio-open-serve   # serves /generate and /health on :5301
```

---

## What Just Happened

- **`AudioMusicModule.configure()`** created a `DynamicModule` carrying `AudioMusicProvider`, exporting the `MusicProvider` contract and `MusicGenerationTask`.
- **`Application.boot()`** ran the provider lifecycle:
  - **register** — `MusicConfig` is bound as a singleton; the provider constructs the configured backend (`LocalHttpMusicProvider` by default) and binds *it* as `MusicProvider`, plus a `MusicGenerationTask` wrapper.
  - **boot** — no extra async I/O (all wiring happened in `register()`).
- Calling `music.generate(MusicRequest(...))` POSTs to `{backend_base_url}/generate` and returns a **`Result[MediaAsset, MusicGenerationError]`** — never raises for a domain failure. The `MediaAsset` carries `mime_type`, `provider`, and `bytes_data`.

---

## Next Steps

- [Guide](./GUIDE.md) — mental model, the four backends, common patterns
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key and env-var override
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Troubleshooting](./TROUBLESHOOTING.md) — common failures and fixes