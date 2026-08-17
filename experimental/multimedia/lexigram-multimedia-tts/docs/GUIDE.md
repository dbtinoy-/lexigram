# Guide: lexigram-multimedia-tts

Learn how to use the text-to-speech subsystem effectively.

---

## Overview

`lexigram-multimedia-tts` synthesizes speech from text. Like its music sibling, it is **backend-agnostic**: your code depends on the `TTSProvider` contract, and `TTSConfig.backend` decides which of the **seven** backends answers — from a zero-config local HTTP server to hosted ElevenLabs/OpenAI APIs to four in-process local model servers.

The umbrella `lexigram-multimedia` auto-discovers it via entry points; it also works standalone through `AudioTTSModule`.

### When to use it

- You need speech narration, voice-overs, accessibility audio, or IVR prompts.
- You want one code path that can switch engines (local → hosted) without rewriting call sites.
- You want graceful degradation: failures come back as `Result[MediaAsset, TTSError]`, not thrown exceptions, except for credential errors.

### Choosing a backend at a glance

| `backend` | Type | Needs extra | Needs key/voice |
|-----------|------|-------------|-----------------|
| `local-http` | any conforming HTTP server | no | no |
| `elevenlabs` | hosted API | `[elevenlabs]` | `elevenlabs_voice_id` + API key |
| `openai` | hosted API | `[openai]` | API key |
| `chatterbox` | local model server `:5100` | `[chatterbox-server]` | no |
| `kokoro` | local model server `:5101` | `[kokoro-server]` | no |
| `f5-tts` | local model server `:5102` (voice cloning) | `[f5-tts-server]` | reference clip + transcript |
| `piper` | local model server `:5103` (CPU, lightest) | `[piper-server]` | no |

---

## Core Concepts

- **`TTSProvider`** — structural protocol (from `lexigram-contracts`): `async generate(request: TTSRequest) -> Result[MediaAsset, MultimediaError]`.
- **`TTSRequest`** — frozen request value: `text`, `voice`, `format` (default `"mp3"`), `reference_audio_uri`, `emotion`, and `extra` for provider-specific data.
- **`MediaAsset`** — frozen result value (`mime_type`, `provider`, `bytes_data`/`uri`, `metadata`); check `has_bytes`/`has_uri`.
- **`TTSError`** — the package error family (leaf of `MultimediaError`, code `LEX_ERR_MM_002`). Returned in `Err(...)` for domain/transport failures.
- **`TTSAuthenticationError`** — raised-not-wrapped when an API key is rejected (401). It's an infrastructure error, so it bypasses the `Result` path.
- **`AudioTTSProvider`** — DI provider (name `"tts"`) that reads `TTSConfig`, resolves secrets, builds the backend, registers it.
- **Reference servers** — `aiohttp` servers that load a model once and serve `/generate` + `/health` (`lexigram-tts-*-serve` scripts).
- **Secrets** — hosted providers get their API key by name from the secrets backend (`AsyncSecretStoreProtocol`), never from config.

---

## Typical Usage

### Plain speech — zero config

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import TTSProvider, TTSRequest
from lexigram.di.module import Module, module
from lexigram.multimedia.tts import AudioTTSModule


@module(imports=[AudioTTSModule.configure()])
class AppModule(Module):
    pass


async def speak() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        tts: TTSProvider = await app.container.resolve(TTSProvider)
        result = await tts.generate(
            TTSRequest(text="Welcome back. Your report is ready.", voice="alloy")
        )
        if result.is_ok():
            asset = result.unwrap()
            print(asset.provider, asset.mime_type)   # local-http audio/mpeg


asyncio.run(speak())
```

- `AudioTTSModule.configure()` defaults to `backend="local-http"` → `LocalHttpTTSProvider` at `http://localhost:5002`.
- One `POST /generate` sends `{text, voice, format}`; the response becomes `MediaAsset.bytes_data`.

### Hosted API with secrets

```python
from lexigram.multimedia.tts import AudioTTSModule
from lexigram.multimedia.tts.config import TTSConfig

module = AudioTTSModule.configure(
    config=TTSConfig(backend="elevenlabs", elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM")
)
```

The provider resolves the key from the secrets backend using `elevenlabs_api_key_secret_name` (default `"elevenlabs_api_key"`) via `resolve_credential`.

---

## Common Patterns

### Pattern: Voice cloning with F5-TTS

`F5TTSProvider` clones a voice from a reference clip. It **requires** both a `reference_audio_uri` (a URI the server fetches — `http(s)://` or `file://`, never inlined bytes) and the clip's transcript in `extra["reference_text"]`. Missing either returns `TTSError` (a request-shape problem, not a crash).

```python
request = TTSRequest(
    text="Now this is the clone speaking.",
    reference_audio_uri="https://cdn.example.com/voice_ref.wav",
    extra={"reference_text": "The original sentence the voice was cloned from."},
)
```

> `request.format` is ignored — the F5-TTS server always returns native WAV.

### Pattern: Emotion-guided speech via an OpenAI-compatible gateway

When `OpenAITTSProvider` receives a `reference_audio_uri`, it switches from the classic `{model, input, voice}` payload to the IndexTTS2 "clone" wire shape (`metadata.audio_url` + `should_use_prompt_for_emotion`), optionally adding an `emotion_prompt`:

```python
request = TTSRequest(
    text="Great to meet you!",
    reference_audio_uri="https://cdn.example.com/ref.wav",
    emotion="cheerful",
)
```

Point `openai_base_url` at your gateway (default `https://api.openai.com`).

### Pattern: Async job execution

Resolve `TTSGenerationTask` from the container and submit via `lexigram-tasks`. `run()` returns a JSON-serializable dict (never raw bytes) — safe for the JSON result store:

```python
task: TTSGenerationTask = await app.container.resolve(TTSGenerationTask)
job = await task.run({
    "text": "Your order has shipped.",
    "voice": "alloy", "format": "mp3", "emotion": "happy",
})
# -> {"provider": ..., "mime_type": ..., "bytes_data": ..., "uri": ..., "metadata": ...}
```

### Pattern: Resilience without code changes

If the container has `RetryPolicyProtocol` and `CircuitBreakerProtocol`, every TTS backend automatically runs its HTTP call via `retry.execute(circuit_breaker.call, ...)` — the provider resolves both during `register()` and injects them.

---

## Integration

- **`lexigram` core** — `Application.boot()`, provider lifecycle (`register` → `boot`), container singletons for `TTSConfig`, `TTSProvider`, `TTSGenerationTask`.
- **`lexigram-contracts`** — `TTSProvider` protocol, `TTSRequest` / `MediaAsset` types, and the error family (`TTSError`, `MultimediaError`, `ProviderNotInstalledError`).
- **Secrets backend** — hosted providers (`elevenlabs`, `openai`) resolve their API key by name through `AsyncSecretStoreProtocol` + `resolve_credential`.
- **`lexigram-resilience`** — optional `RetryPolicyProtocol` / `CircuitBreakerProtocol` injection.
- **`lexigram-tasks`** — `TTSGenerationTask` is a compatible handler for the async job path.
- **`lexigram-multimedia` umbrella** — entry points `lexigram.multimedia.subsystems: tts` and `lexigram.multimedia.modules: tts` enable auto-discovery.

---

## Best Practices

- ✅ Use `backend="local-http"` (or `piper`) for development and CI — no keys, light compute, sub-second cold start.
- ✅ Resolve `TTSProvider` from the container — never instantiate backend classes manually.
- ✅ Always check `result.is_ok()` / `result.unwrap_err()`; `TTSAuthenticationError` will be raised, not returned.
- ✅ Store API keys exclusively in the secrets backend and reference them by name (`elevenlabs_api_key`, `openai_api_key`).
- ✅ Run local model servers in a dedicated venv so torch/ONNX weights stay out of your app process.
- ✅ Keep F5-TTS reference audio as a URI the server fetches; never inline bytes through `reference_audio_uri`.
- ❌ Don't call `result.unwrap()` blindly — it raises on `Err`.
- ❌ Don't use `backend="elevenlabs"` without setting `elevenlabs_voice_id` — `AudioTTSProvider.register()` raises `ProviderNotInstalledError` ("required when backend='elevenlabs'").
- ❌ Don't expect `request.format` to control output on Chatterbox, F5-TTS, Kokoro, or Piper — they always return native WAV.
- ❌ Don't hardcode secrets in `application.yaml`.

---

## Next Steps

- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
- [Troubleshooting](./TROUBLESHOOTING.md) — common failures and fixes