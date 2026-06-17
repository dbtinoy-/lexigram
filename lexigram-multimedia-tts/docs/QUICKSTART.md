# Quickstart: lexigram-multimedia-tts

Synthesize speech from text, wired through the Lexigram DI container. The default backend hits a local HTTP reference server, so it works with **zero API keys** — no cloud account, no secret setup.

---

## Install

```bash
uv add lexigram-multimedia-tts
```

Optional extras pull in a backend's SDK or server runtime:

```bash
uv add "lexigram-multimedia-tts[elevenlabs]"        # ElevenLabs API
uv add "lexigram-multimedia-tts[openai]"            # OpenAI TTS API
uv add "lexigram-multimedia-tts[chatterbox-server]" # local Chatterbox (torch)
uv add "lexigram-multimedia-tts[kokoro-server]"     # local Kokoro-82M
uv add "lexigram-multimedia-tts[f5-tts-server]"     # local F5-TTS voice cloning (torch)
uv add "lexigram-multimedia-tts[piper-server]"      # local Piper (ONNX, CPU)
```

> `lexigram-multimedia-tts` depends on `lexigram` and `lexigram-contracts` (installed automatically). `aiohttp` is a hard dependency used by every backend.

---

## Minimal Working Example

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import TTSProvider, TTSRequest
from lexigram.di.module import Module, module
from lexigram.multimedia.tts import AudioTTSModule


@module(imports=[AudioTTSModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        tts: TTSProvider = await app.container.resolve(TTSProvider)
        result = await tts.generate(TTSRequest(text="Hello from Lexigram", voice="alloy"))
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — raw audio bytes
            print(asset.mime_type, asset.has_bytes)


asyncio.run(main())
```

Point the `local-http` backend at any TTS HTTP server exposing `POST /generate` (the simplest path is a Coqui/Piper-style server on port `5002`).

---

## What Just Happened

- **`AudioTTSModule.configure()`** created a `DynamicModule` carrying `AudioTTSProvider`, exporting the `TTSProvider` contract and `TTSGenerationTask`.
- **`Application.boot()`** ran the provider lifecycle:
  - **register** — `TTSConfig` is bound as a singleton; the provider builds the configured backend (`LocalHttpTTSProvider` by default) and binds *it* as `TTSProvider`, plus a `TTSGenerationTask` wrapper. API backends additionally resolve their API key from the secrets backend by name.
  - **boot** — no extra async I/O (all wiring happened in `register()`).
- `tts.generate(TTSRequest(...))` POSTs to `{backend_base_url}/generate` and returns a **`Result[MediaAsset, TTSError]`** — domain failures are values, not exceptions. `MediaAsset` carries `mime_type`, `provider`, `bytes_data`.

---

## Next Steps

- [Guide](./GUIDE.md) — mental model, the seven backends, common patterns
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key and env-var override
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Troubleshooting](./TROUBLESHOOTING.md) — common failures and fixes