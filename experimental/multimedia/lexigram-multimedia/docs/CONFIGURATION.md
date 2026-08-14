# Configuration

Configuration options for `lexigram-multimedia` — the umbrella config plus per-subsystem trees.

---

## Overview

Loaded from the `multimedia:` section of `application.yaml`. Environment variable prefix:
`LEX_MULTIMEDIA__`.

`MultimediaConfig` (extends `lexigram.config.BaseConfig`) declares
`config_section = "multimedia"`, so framework config loading maps the YAML/evn-tree to this
dataclass. The seven subsystem configs are nested dataclasses — each sibling package owns
its own config model and its own defaults; the umbrella simply composes them.

```yaml
multimedia:
  storage_path_prefix: "multimedia/"
  cache_results: false
  tts:
    backend: "local-http"
  music:
    backend: "local-http"
  video:
    backend: "local-http"
  image:
    backend: "local-http"
  upscale:
    backend: "real-esrgan"
  interpolate:
    backend: "rife"
  beat:
    backend: "librosa"
```

---

## Basic Example

```python
from lexigram.multimedia import MultimediaConfig, MultimediaModule

module = MultimediaModule.configure(
    config=MultimediaConfig(
        storage_path_prefix="media/",
        cache_results=True,
    )
)
app.add_module(module)
```

Calling `MultimediaModule.configure()` with no arguments builds the same default configs.

---

## Options

### Top-level `MultimediaConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tts` | `TTSConfig` | `TTSConfig()` | TTS subsystem config (lexigram-multimedia-tts) |
| `music` | `MusicConfig` | `MusicConfig()` | Music generation config (lexigram-multimedia-music) |
| `video` | `VideoConfig` | `VideoConfig()` | Video generation + processing config (lexigram-multimedia-video) |
| `image` | `ImageConfig` | `ImageConfig()` | Image generation config (lexigram-multimedia-image) |
| `upscale` | `UpscaleConfig` | `UpscaleConfig()` | Upscale config (lexigram-multimedia-upscale) |
| `interpolate` | `InterpolationConfig` | `InterpolationConfig()` | Frame interpolation config (lexigram-multimedia-interpolate) |
| `beat` | `BeatAnalysisConfig` | `BeatAnalysisConfig()` | Beat analysis config (lexigram-multimedia-beat) |
| `storage_path_prefix` | `str` | `"multimedia/"` | Blob-storage key prefix for generated assets |
| `cache_results` | `bool` | `False` | Cache accessor `generate()` results in the cache backend |

### Per-subsystem fields (notable defaults)

Each nested config carries its backend selector; the full field list lives in each
sibling package's docs.

| Subsystem | Field | Type | Default | Description |
|-----------|-------|------|---------|-------------|
| `tts` | `backend` | `str` | `"local-http"` | `local-http`, `elevenlabs`, `openai`, `chatterbox`, `kokoro`, `f5-tts`, `piper` |
| `tts` | `elevenlabs_voice_id` | `str \| None` | `null` | Required for the `elevenlabs` backend |
| `music` | `backend` | `str` | `"local-http"` | `local-http`, `stability-audio`, `ace-step`, `stable-audio-open` |
| `video` | `backend` | `str` | `"local-http"` | `local-http`, `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui` |
| `video` | `processing.max_concurrent_jobs` | `int` | `2` | FFmpeg processing concurrency limit |
| `image` | `backend` | `str` | `"local-http"` | `local-http`, `stability`, `openai`, `comfyui` |
| `upscale` | `backend` | `str` | `"real-esrgan"` | `real-esrgan` or `hat` |
| `interpolate` | `backend` | `str` | `"rife"` | RIFE frame-interpolation backend |
| `beat` | `backend` | `str` | `"librosa"` | `librosa` (in-process) or `madmom` (reference server) |
| `beat` | `librosa_sample_rate` | `int` | `22050` | Sample rate for the librosa backend |
| `beat` | `madmom_base_url` | `str` | `"http://localhost:5600"` | Madmom reference-server URL |

---

## Environment Variables

The env var name is the config path in SCREAMING tokens joined by `__` under
`LEX_MULTIMEDIA__`. Nested subsystem fields prefix with the subsystem name.

| Variable | Description |
|---------|-------------|
| `LEX_MULTIMEDIA__STORAGE_PATH_PREFIX` | Blob storage prefix for assets (`multimedia/`) |
| `LEX_MULTIMEDIA__CACHE_RESULTS` | Enable result caching (`true`/`false`) |
| `LEX_MULTIMEDIA__TTS__BACKEND` | TTS backend name |
| `LEX_MULTIMEDIA__TTS__ELEVENLABS_VOICE_ID` | ElevenLabs voice id |
| `LEX_MULTIMEDIA__MUSIC__BACKEND` | Music backend name |
| `LEX_MULTIMEDIA__VIDEO__BACKEND` | Video backend name |
| `LEX_MULTIMEDIA__IMAGE__BACKEND` | Image backend name |
| `LEX_MULTIMEDIA__UPSCALE__BACKEND` | Upscale backend name |
| `LEX_MULTIMEDIA__INTERPOLATE__BACKEND` | Interpolation backend name |
| `LEX_MULTIMEDIA__BEAT__BACKEND` | Beat backend name (`librosa`/`madmom`) |
| `LEX_MULTIMEDIA__BEAT__MADMOM_BASE_URL` | Madmom server URL |

```bash
LEX_MULTIMEDIA__TTS__BACKEND=elevenlabs \
LEX_MULTIMEDIA__TTS__ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM \
LEX_MULTIMEDIA__VIDEO__BACKEND=local-http \
LEX_MULTIMEDIA__CACHE_RESULTS=true \
  python -m my_app
```

> A subsystem installed standalone uses its own prefix instead —
> e.g. `LEX_MULTIMEDIA_BEAT__BACKEND` (see the beat package's Configuration doc).

---

## Advanced Configuration

### Programmatic sub-config overrides

```python
from lexigram.multimedia import MultimediaConfig, MultimediaModule
from lexigram.multimedia.tts.config import TTSConfig
from lexigram.multimedia.beat.config import BeatAnalysisConfig

app.add_module(
    MultimediaModule.configure(
        config=MultimediaConfig(
            tts=TTSConfig(backend="elevenlabs", elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM"),
            beat=BeatAnalysisConfig(backend="madmom", madmom_base_url="http://10.0.0.5:5600"),
            storage_path_prefix="prod/media/",
        )
    )
)
```

### Standalone subsystem usage

Every subsystem can also be wired on its own with its own module — the umbrella is never
required:

```python
from lexigram.multimedia.beat.module import BeatAnalysisModule
from lexigram.multimedia.beat.config import BeatAnalysisConfig

app.add_module(BeatAnalysisModule.configure(config=BeatAnalysisConfig(backend="librosa")))
```

### Using `.stub()` for tests

```python
# Stubs all installed subsystems; no servers, no network
app.add_module(MultimediaModule.stub())
```

`stub()` imports each core subsystem's `.stub()` module (`AudioTTSModule.stub(...)`,
`AudioMusicModule.stub(...)`, …) and also loads any non-core modules discovered via the
`lexigram.multimedia.modules` entry-point group.

---

## Best Practices

- Keep the umbrella config minimal; override only what your deployment differs on.
- Prefer environment variables for secrets and per-environment switches
  (`LEX_MULTIMEDIA__TTS__BACKEND=elevenlabs`), YAML for structure.
- Never hardcode API keys in `application.yaml` — subsystem configs accept
  `*_api_key_secret_name` fields that reference secrets-manager entries.
- Enable `cache_results` only when a cache backend is present; otherwise the flag is inert.
- Give every environment its own `storage_path_prefix` to avoid cross-env asset collisions.