# Configuration

Configuration options for `lexigram-multimedia-beat`.

---

## Overview

Loaded from the `multimedia_beat:` section of `application.yaml` when installed
standalone, or from `multimedia.beat:` when nested under the `lexigram-multimedia`
umbrella. Environment variable prefix: `LEX_MULTIMEDIA_BEAT__`.

`BeatAnalysisConfig` extends `lexigram.config.BaseConfig` and declares
`config_section = "multimedia_beat"`, so framework config loading maps the YAML/env tree
onto it and `BeatAnalysisGenerationProvider` consumes the instance directly.

```yaml
multimedia_beat:
  backend: "librosa"            # librosa (in-process) | madmom (reference server)
  librosa_sample_rate: 22050
  madmom_base_url: "http://localhost:5600"
  timeout: 30.0
```

---

## Basic Example

```python
from lexigram.multimedia.beat import BeatAnalysisModule
from lexigram.multimedia.beat.config import BeatAnalysisConfig

app.add_module(
    BeatAnalysisModule.configure(
        config=BeatAnalysisConfig(backend="madmom", timeout=60.0)
    )
)
```

`BeatAnalysisModule.configure()` with no arguments uses `BeatAnalysisConfig()` —
the in-process `librosa` backend. `stub()` also forces `librosa` regardless of YAML, which
keeps tests server-free.

---

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backend` | `Literal["librosa", "madmom"]` | `"librosa"` | Backend selection. `librosa` runs in-process (needs the `[librosa]` extra); `madmom` calls a reference server (needs `[madmom-server]`) |
| `librosa_sample_rate` | `int` | `22050` | Sample rate passed to `librosa.load()` by `LibrosaBeatAnalysisProvider` |
| `madmom_base_url` | `str` | `"http://localhost:5600"` | Base URL of the madmom server; `POST {base}/analyze`, `GET {base}/health` |
| `timeout` | `float` | `30.0` | HTTP timeout (seconds) for madmom requests (`aiohttp.ClientTimeout(total=...)`) |

An unknown `backend` value raises `ProviderNotInstalledError` from contracts at
`register()` time — startup fails fast with an actionable message rather than at first
request.

---

## Environment Variables

| Variable | Description |
|---------|-------------|
| `LEX_MULTIMEDIA_BEAT__BACKEND` | Beat backend: `librosa` or `madmom` |
| `LEX_MULTIMEDIA_BEAT__LIBROSA_SAMPLE_RATE` | Sample rate for the librosa backend |
| `LEX_MULTIMEDIA_BEAT__MADMOM_BASE_URL` | Madmom reference-server URL |
| `LEX_MULTIMEDIA_BEAT__TIMEOUT` | Request timeout in seconds |

```bash
LEX_MULTIMEDIA_BEAT__BACKEND=madmom \
LEX_MULTIMEDIA_BEAT__MADMOM_BASE_URL=http://10.0.0.5:5600 \
LEX_MULTIMEDIA_BEAT__TIMEOUT=60.0 \
  python -m my_app
```

> Under the umbrella, the nested key uses `multimedia:`:
> `LEX_MULTIMEDIA__BEAT__BACKEND=madmom` — see the umbrella's Configuration doc.

---

## Advanced Configuration

### Two profiles, one deployment

```yaml
multimedia_beat:
  backend: "madmom"
  madmom_base_url: "http://beat-worker:5600"
  timeout: 60.0

# off in local dev — include this small override file
multimedia_beat:
  backend: "librosa"
```

### Full programmatic setup (madmom + resilience)

```python
from lexigram.multimedia.beat import BeatAnalysisModule
from lexigram.multimedia.beat.config import BeatAnalysisConfig
from lexigram.resilience import ResilienceModule

app.add_module(ResilienceModule.configure())
app.add_module(
    BeatAnalysisModule.configure(
        config=BeatAnalysisConfig(
            backend="madmom",
            madmom_base_url="http://localhost:5600",
            timeout=30.0,
        )
    )
)
```

`BeatAnalysisGenerationProvider.register()` resolves `RetryPolicyProtocol` and
`CircuitBreakerProtocol` optionally — configured via `ResilienceConfig` — and passes them
to `MadmomBeatAnalysisProvider` so server calls are protected end to end.

---

## Best Practices

- Start with `librosa`; move to `madmom` only when syncopation/accuracy demands it.
- Keep `timeout` comfortably above the madmom model's per-request latency (30 s default is
  conservative for most content).
- Never version a `madmom_base_url` pointing at a local machine into production — use env
  vars or a service name.
- Pin `librosa_sample_rate` to your source material's native rate to avoid resampling
  artifacts.
- In tests, prefer `BeatAnalysisModule.stub()` so no server and no extra install is needed.