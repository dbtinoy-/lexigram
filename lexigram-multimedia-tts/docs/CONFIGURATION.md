# Configuration: lexigram-multimedia-tts

Configuration options for the TTS subsystem. Everything is driven by one dataclass — `TTSConfig` in `src/lexigram/multimedia/tts/config.py`.

---

## Overview

`TTSConfig` extends `BaseConfig` and declares `config_section = "multimedia_tts"`. Three ways to configure, from highest precedence:

1. **Python** — `AudioTTSModule.configure(config=TTSConfig(...))` (the `_requested_config` the provider honors first).
2. **Environment variables** — prefix `LEX_MULTIMEDIA__TTS__`, e.g. `LEX_MULTIMEDIA__TTS__BACKEND=openai`.
3. **YAML** — the `multimedia_tts:` section of `application.yaml` (provider `config_key` is `"multimedia_tts"`).

The provider binds the resolved `TTSConfig` as a container singleton, so consumers can inject it:

```python
from lexigram.multimedia.tts.config import TTSConfig

config: TTSConfig = await app.container.resolve(TTSConfig)
```

For the umbrella integration, YAML nests under `multimedia: → tts:`; standalone, pass `TTSConfig` directly to `AudioTTSModule.configure()`.

**API keys are never config values.** `TTSConfig` only names *where* the key lives (`elevenlabs_api_key_secret_name`, `openai_api_key_secret_name`); the provider fetches the actual value from the secrets backend via `resolve_credential`.

---

## Basic Example

```yaml
multimedia_tts:
  backend: "elevenlabs"
  elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM"   # required for backend=elevenlabs
  elevenlabs_api_key_secret_name: "elevenlabs_api_key"
```

```python
from lexigram.multimedia.tts import AudioTTSModule

module = AudioTTSModule.configure()  # reads application.yaml / env vars
```

---

## Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `config_section` | `ClassVar[str]` | `"multimedia_tts"` | YAML section key for file-based config |
| `backend` | `Literal["local-http", "elevenlabs", "openai", "chatterbox", "kokoro", "f5-tts", "piper"]` | `"local-http"` | Which TTS backend the provider instantiates |
| `local_http_base_url` | `str` | `"http://localhost:5002"` | Base URL of a self-hosted TTS server (`/generate`, `/health`) |
| `elevenlabs_voice_id` | `str \| None` | `None` | ElevenLabs voice ID — **required** when `backend="elevenlabs"` (missing → `ProviderNotInstalledError`) |
| `elevenlabs_api_key_secret_name` | `str` | `"elevenlabs_api_key"` | Secrets-store name of the ElevenLabs API key |
| `openai_api_key_secret_name` | `str` | `"openai_api_key"` | Secrets-store name of the OpenAI API key |
| `openai_voice` | `str` | `"alloy"` | Default OpenAI voice (alloy, echo, fable, onyx, nova, shimmer) |
| `openai_model` | `str` | `"tts-1"` | OpenAI TTS model id |
| `openai_base_url` | `str` | `"https://api.openai.com"` | OpenAI-compatible base URL — point at a gateway for cloning/alternative models |
| `chatterbox_base_url` | `str` | `"http://localhost:5100"` | Chatterbox reference server URL |
| `chatterbox_exaggeration` | `float` | `0.5` | Chatterbox exaggeration factor |
| `chatterbox_cfg_weight` | `float` | `0.5` | Chatterbox classifier-free guidance weight |
| `chatterbox_temperature` | `float` | `0.85` | Chatterbox sampling temperature |
| `kokoro_base_url` | `str` | `"http://localhost:5101"` | Kokoro-82M reference server URL |
| `kokoro_default_voice` | `str` | `"af_heart"` | Kokoro voice used when the request has none |
| `f5_tts_base_url` | `str` | `"http://localhost:5102"` | F5-TTS voice-cloning reference server URL |
| `piper_base_url` | `str` | `"http://localhost:5103"` | Piper reference server URL |
| `piper_default_voice` | `str` | `"en_US-lessac-medium"` | Piper voice used when the request has none |
| `timeout` | `float` | `60.0` | HTTP request timeout (seconds) applied to every backend call |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LEX_MULTIMEDIA__TTS__BACKEND` | Backend selector: `local-http`, `elevenlabs`, `openai`, `chatterbox`, `kokoro`, `f5-tts`, `piper` |
| `LEX_MULTIMEDIA__TTS__LOCAL_HTTP_BASE_URL` | URL of the self-hosted local-http server |
| `LEX_MULTIMEDIA__TTS__ELEVENLABS_VOICE_ID` | ElevenLabs voice ID |
| `LEX_MULTIMEDIA__TTS__ELEVENLABS_API_KEY_SECRET_NAME` | Secrets name for the ElevenLabs key |
| `LEX_MULTIMEDIA__TTS__OPENAI_API_KEY_SECRET_NAME` | Secrets name for the OpenAI key |
| `LEX_MULTIMEDIA__TTS__OPENAI_VOICE` | Default OpenAI voice |
| `LEX_MULTIMEDIA__TTS__OPENAI_MODEL` | OpenAI TTS model |
| `LEX_MULTIMEDIA__TTS__OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `LEX_MULTIMEDIA__TTS__CHATTERBOX_BASE_URL` | Chatterbox server URL |
| `LEX_MULTIMEDIA__TTS__CHATTERBOX_EXAGGERATION` | Chatterbox exaggeration |
| `LEX_MULTIMEDIA__TTS__CHATTERBOX_CFG_WEIGHT` | Chatterbox CFG weight |
| `LEX_MULTIMEDIA__TTS__CHATTERBOX_TEMPERATURE` | Chatterbox temperature |
| `LEX_MULTIMEDIA__TTS__KOKORO_BASE_URL` | Kokoro server URL |
| `LEX_MULTIMEDIA__TTS__KOKORO_DEFAULT_VOICE` | Default Kokoro voice |
| `LEX_MULTIMEDIA__TTS__F5_TTS_BASE_URL` | F5-TTS server URL |
| `LEX_MULTIMEDIA__TTS__PIPER_BASE_URL` | Piper server URL |
| `LEX_MULTIMEDIA__TTS__PIPER_DEFAULT_VOICE` | Default Piper voice |
| `LEX_MULTIMEDIA__TTS__TIMEOUT` | Request timeout in seconds |

```bash
LEX_MULTIMEDIA__TTS__BACKEND=openai \
LEX_MULTIMEDIA__TTS__OPENAI_VOICE=echo \
LEX_MULTIMEDIA__TTS__OPENAI_MODEL=tts-1-hd \
  python -m your_app
```

---

## Advanced Configuration

### ElevenLabs voice cloning

ElevenLabs' hosted endpoints also accept a `reference_audio_uri` on the request — no extra config keys; just send the field and let `request.format` default:

```python
config = TTSConfig(
    backend="elevenlabs",
    elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM",
    elevenlabs_api_key_secret_name="elevenlabs_api_key",
)
```

### OpenAI-compatible gateways

Keep the classic `TTSConfig`, but point `openai_base_url` at a gateway that speaks `/v1/audio/speech`:

```python
config = TTSConfig(
    backend="openai",
    openai_base_url="https://tts-gateway.internal",
    openai_model="index-tts2",
    openai_voice="alloy",
)
```

Requests with `reference_audio_uri` automatically use the IndexTTS2 clone wire shape (`metadata.audio_url`) instead of the classic `{model, input, voice}` payload.

### Deployment-shaped env overrides

```yaml
# application.yaml
multimedia_tts:
  backend: "local-http"
  local_http_base_url: "http://localhost:5002"

# prod overrides only — no code change
# LEX_MULTIMEDIA__TTS__BACKEND=kokoro
# LEX_MULTIMEDIA__TTS__KOKORO_BASE_URL=http://tts.internal:5101
```

---

## Best Practices

- Keep config minimal — most deployments need `backend` + one base URL (or one voice id) + `timeout`.
- Prefer environment variables for deployment-specific values; keep `application.yaml` generic.
- **Never store API keys in config or YAML** — reference them by name and let `AsyncSecretStoreProtocol` resolve them.
- Set `elevenlabs_voice_id` before switching to `backend="elevenlabs"` — registration fails fast otherwise.
- Choose `timeout` per backend temperament: Piper is fast (15s default in the provider), F5-TTS slower (90s), hosted APIs vary.