# lexigram-multimedia-tts

Text-to-speech generation for the Lexigram Framework — local and API-based backends (`local-http`, `elevenlabs`, `openai`, `chatterbox`, `kokoro`, `f5-tts`, `piper`).

---

## Overview

`lexigram-multimedia-tts` synthesizes speech from text. The default backend calls a local HTTP reference server (`http://localhost:5002`) so the package works out of the box with no API keys; hosted backends (ElevenLabs, OpenAI) and in-process reference servers (Chatterbox, Kokoro, F5-TTS, Piper) are selectable via config.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-multimedia-tts
# Optional extras
uv add "lexigram-multimedia-tts[elevenlabs]"        # ElevenLabs API
uv add "lexigram-multimedia-tts[openai]"            # OpenAI TTS API
uv add "lexigram-multimedia-tts[chatterbox-server]" # local Chatterbox server (torch)
uv add "lexigram-multimedia-tts[kokoro-server]"     # local Kokoro server
uv add "lexigram-multimedia-tts[f5-tts-server]"     # local F5-TTS server (torch)
uv add "lexigram-multimedia-tts[piper-server]"      # local Piper server
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.multimedia.tts import AudioTTSModule
from lexigram.contracts.multimedia import TTSProvider, TTSRequest


@module(imports=[AudioTTSModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        tts = await app.container.resolve(TTSProvider)
        result = await tts.generate(TTSRequest(text="Hello from Lexigram", voice="alloy"))
        if result.is_ok():
            asset = result.unwrap()  # MediaAsset — audio bytes or URI


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `AudioTTSModule.configure()` with no arguments to use the `local-http` backend at `http://localhost:5002`.

### Option 1 — YAML file

```yaml
# application.yaml
multimedia:
  tts:
    backend: "elevenlabs"
    elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM"
```

### Option 2 — Profiles + Environment Variables

```bash
export LEX_PROFILE=production
export LEX_MULTIMEDIA__TTS__BACKEND=openai
export LEX_MULTIMEDIA__TTS__OPENAI_VOICE=echo
```

### Option 3 — Python

```python
from lexigram.multimedia.tts import AudioTTSModule
from lexigram.multimedia.tts.config import TTSConfig

AudioTTSModule.configure(
    config=TTSConfig(backend="elevenlabs", elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM")
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend` | `"local-http"` | `LEX_MULTIMEDIA__TTS__BACKEND` | `local-http`, `elevenlabs`, `openai`, `chatterbox`, `kokoro`, `f5-tts`, `piper` |
| `local_http_base_url` | `"http://localhost:5002"` | `LEX_MULTIMEDIA__TTS__LOCAL_HTTP_BASE_URL` | Local reference server URL |
| `elevenlabs_voice_id` | `None` | `LEX_MULTIMEDIA__TTS__ELEVENLABS_VOICE_ID` | ElevenLabs voice ID (required for `elevenlabs`) |
| `elevenlabs_api_key_secret_name` | `"elevenlabs_api_key"` | `LEX_MULTIMEDIA__TTS__ELEVENLABS_API_KEY_SECRET_NAME` | Secret name for the ElevenLabs API key |
| `openai_api_key_secret_name` | `"openai_api_key"` | `LEX_MULTIMEDIA__TTS__OPENAI_API_KEY_SECRET_NAME` | Secret name for the OpenAI API key |
| `openai_voice` | `"alloy"` | `LEX_MULTIMEDIA__TTS__OPENAI_VOICE` | OpenAI voice (`alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`) |
| `openai_model` | `"tts-1"` | `LEX_MULTIMEDIA__TTS__OPENAI_MODEL` | OpenAI TTS model |
| `openai_base_url` | `"https://api.openai.com"` | `LEX_MULTIMEDIA__TTS__OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `chatterbox_base_url` | `"http://localhost:5100"` | `LEX_MULTIMEDIA__TTS__CHATTERBOX_BASE_URL` | Chatterbox server URL |
| `chatterbox_exaggeration` | `0.5` | `LEX_MULTIMEDIA__TTS__CHATTERBOX_EXAGGERATION` | Chatterbox exaggeration factor |
| `chatterbox_cfg_weight` | `0.5` | `LEX_MULTIMEDIA__TTS__CHATTERBOX_CFG_WEIGHT` | Chatterbox classifier-free guidance weight |
| `chatterbox_temperature` | `0.85` | `LEX_MULTIMEDIA__TTS__CHATTERBOX_TEMPERATURE` | Chatterbox sampling temperature |
| `kokoro_base_url` | `"http://localhost:5101"` | `LEX_MULTIMEDIA__TTS__KOKORO_BASE_URL` | Kokoro server URL |
| `kokoro_default_voice` | `"af_heart"` | `LEX_MULTIMEDIA__TTS__KOKORO_DEFAULT_VOICE` | Default Kokoro voice |
| `f5_tts_base_url` | `"http://localhost:5102"` | `LEX_MULTIMEDIA__TTS__F5_TTS_BASE_URL` | F5-TTS server URL |
| `piper_base_url` | `"http://localhost:5103"` | `LEX_MULTIMEDIA__TTS__PIPER_BASE_URL` | Piper server URL |
| `piper_default_voice` | `"en_US-lessac-medium"` | `LEX_MULTIMEDIA__TTS__PIPER_DEFAULT_VOICE` | Default Piper voice |
| `timeout` | `60.0` | `LEX_MULTIMEDIA__TTS__TIMEOUT` | Request timeout in seconds |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AudioTTSModule.configure(config)` | Configure with explicit TTS config |
| `AudioTTSModule.stub()` | Real module pinned to the default `local-http` backend for tests |

## Key Features

- **Seven backends** — `local-http`, `elevenlabs`, `openai`, `chatterbox`, `kokoro`, `f5-tts`, `piper`
- **Reference servers** — `lexigram-tts-*-serve` console scripts run each local model server
- **Secret-managed API keys** — provider keys resolved by name through the secrets backend
- **Result-based** — `generate() -> Result[MediaAsset, MultimediaError]`; errors are domain values, not exceptions

## Testing

```python
from lexigram import Application
from lexigram.multimedia.tts import AudioTTSModule

async def test_boot():
    async with Application.boot(modules=[AudioTTSModule.stub()]) as app:
        assert app.container is not None
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/multimedia/tts/module.py` | `AudioTTSModule.configure()` and `.stub()` |
| `src/lexigram/multimedia/tts/config.py` | `TTSConfig` |
| `src/lexigram/multimedia/tts/di/provider.py` | `AudioTTSProvider` — registers `TTSProvider`, wires task handlers |
| `src/lexigram/multimedia/tts/providers/` | Backend implementations (`local_http`, `elevenlabs`, `openai`, `chatterbox`, `kokoro`, `f5_tts`, `piper`) |
| `src/lexigram/multimedia/tts/servers/` | Reference-server entry points (`lexigram-tts-*-serve`) |
| `src/lexigram/multimedia/tts/tasks.py` | Background generation task handlers |
| `src/lexigram/multimedia/tts/exceptions.py` | `TTSError` hierarchy |
