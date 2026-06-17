# Configuration: lexigram-multimedia-music

Configuration options for the music generation subsystem. Everything is driven by one dataclass — `MusicConfig` in `src/lexigram/multimedia/music/config.py`.

---

## Overview

`MusicConfig` extends `BaseConfig` and declares `config_section = "multimedia_music"`. Three ways to configure, from highest precedence:

1. **Python** — `AudioMusicModule.configure(config=MusicConfig(...))` (the `_requested_config` the provider honors first).
2. **Environment variables** — prefix `LEX_MULTIMEDIA_MUSIC__`, e.g. `LEX_MULTIMEDIA_MUSIC__BACKEND=ace-step`.
3. **YAML** — the `multimedia_music:` section of `application.yaml` (`config_key` on the provider is `"multimedia_music"`).

The provider binds the resolved `MusicConfig` as a container singleton, so any consumer can inject it:

```python
from lexigram.multimedia.music.config import MusicConfig

config: MusicConfig = await app.container.resolve(MusicConfig)
```

For the umbrella integration, YAML nests under `multimedia: → music:` (the umbrella's `MultimediaProvider` maps it); standalone, pass `MusicConfig` directly to `AudioMusicModule.configure()`.

---

## Basic Example

```yaml
multimedia_music:
  backend: "ace-step"
  ace_step_base_url: "http://localhost:5300"
  timeout: 120.0
```

```python
from lexigram.multimedia.music import AudioMusicModule

module = AudioMusicModule.configure()  # reads application.yaml / env vars
```

---

## Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `config_section` | `ClassVar[str]` | `"multimedia_music"` | YAML section key for file-based config |
| `backend` | `Literal["local-http", "stability-audio", "ace-step", "stable-audio-open"]` | `"local-http"` | Which music backend the provider instantiates |
| `local_http_base_url` | `str` | `"http://localhost:5003"` | Base URL of the self-hosted local-http server (`/generate`, `/health`) |
| `ace_step_base_url` | `str` | `"http://localhost:5300"` | Base URL of the ACE-Step reference server |
| `stable_audio_open_base_url` | `str` | `"http://localhost:5301"` | Base URL of the Stable Audio Open reference server |
| `timeout` | `float` | `60.0` | HTTP request timeout (seconds) applied to every backend call |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LEX_MULTIMEDIA_MUSIC__BACKEND` | Backend selector: `local-http`, `stability-audio`, `ace-step`, `stable-audio-open` |
| `LEX_MULTIMEDIA_MUSIC__LOCAL_HTTP_BASE_URL` | URL of the local-http server |
| `LEX_MULTIMEDIA_MUSIC__ACE_STEP_BASE_URL` | URL of the ACE-Step reference server |
| `LEX_MULTIMEDIA_MUSIC__STABLE_AUDIO_OPEN_BASE_URL` | URL of the Stable Audio Open reference server |
| `LEX_MULTIMEDIA_MUSIC__TIMEOUT` | Request timeout in seconds |

```bash
LEX_MULTIMEDIA_MUSIC__BACKEND=ace-step \
LEX_MULTIMEDIA_MUSIC__ACE_STEP_BASE_URL=http://10.0.0.5:5300 \
LEX_MULTIMEDIA_MUSIC__TIMEOUT=180 \
  python -m your_app
```

---

## Advanced Configuration

### Backends that are not yet implemented

`backend="stability-audio"` is a **stub**: the provider raises `ProviderNotInstalledError` ("not yet implemented") at `register()` time — eagerly, with an actionable message, rather than failing on the first request. The literal is accepted by `MusicConfig` typing, but picking it at runtime is an error until an implementation lands (see `providers/stability_audio.py`).

### Programmatic environment switching

```python
import os

from lexigram.multimedia.music import AudioMusicModule
from lexigram.multimedia.music.config import MusicConfig

backend = os.getenv("MUSIC_BACKEND", "local-http")
module = AudioMusicModule.configure(config=MusicConfig(backend=backend))  # type: ignore[arg-type]
```

### Per-environment overrides

```yaml
# application.yaml
multimedia_music:
  backend: "local-http"
  local_http_base_url: "http://localhost:5003"

# production overrides via env — no code change
# LEX_MULTIMEDIA_MUSIC__BACKEND=stable-audio-open
# LEX_MULTIMEDIA_MUSIC__STABLE_AUDIO_OPEN_BASE_URL=http://models.internal:5301
```

---

## Best Practices

- Keep config minimal — `backend` + one base URL + `timeout` covers 95% of setups.
- Prefer environment variables for deployment-specific values (host, port, backend choice).
- Never hardcode secrets — hosted backends' API keys will flow through the secrets backend (`AsyncSecretStoreProtocol`), not config, when implemented.
- Don't rely on the `stability-audio` backend — it's a deliberate stub until a provider exists.
- Set `timeout` above your longest expected generation — 60s default is tuned for short FX, not 2-minute songs.