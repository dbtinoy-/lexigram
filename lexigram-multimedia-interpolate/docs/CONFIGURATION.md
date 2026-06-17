# Configuration

All configuration options for `lexigram-multimedia-interpolate`.

---

## Overview

`InterpolationConfig` extends `BaseConfig` (stdlib dataclasses, not pydantic)
and declares its section via `config_section = "multimedia_interpolate"`.
Loading follows the canonical `BaseConfig.from_yaml()` order — each later
source overrides the previous:

1. `application.yaml` values (base layer)
2. Profile overlay `application.{LEX_PROFILE}.yaml` (if set)
3. `LEX_*` environment variables

`InterpolationGenerationProvider` passes the section into the container
(`config_key = "multimedia_interpolate"`). Under the `lexigram-multimedia`
umbrella, the same keys nest as `multimedia: interpolate:`.

The config surface is deliberately tiny: frame-pair interpolation needs only a
backend, a server URL, and a timeout. There is no factor/fps knob here — those
are per-call arguments on `VideoInterpolationService.interpolate_video()`.

## Basic Example

```yaml
# application.yaml
multimedia_interpolate:
  backend: "rife"
  rife_base_url: "http://localhost:5500"
  timeout: 30.0
```

```python
config = InterpolationConfig.from_yaml("application.yaml")  # section used automatically
assert config.backend == "rife"
```

Programmatic equivalent:

```python
from lexigram.multimedia.interpolate import InterpolationModule
from lexigram.multimedia.interpolate.config import InterpolationConfig

module = InterpolationModule.configure(config=InterpolationConfig(timeout=30.0))
```

## Options

All fields of `InterpolationConfig`:

| Option | Type | Default | Description |
|-------|------|--------|------------|
| `backend` | `Literal["rife"]` | `"rife"` | Interpolation backend to register (only `rife` is implemented) |
| `rife_base_url` | `str` | `"http://localhost:5500"` | Base URL of the RIFE reference server |
| `timeout` | `float` | `15.0` | HTTP request timeout in seconds for `/interpolate` |

## Environment Variables

Prefix: `LEX_MULTIMEDIA__INTERPOLATE__` (umbrella-layout YAML) or
`LEX_MULTIMEDIA_INTERPOLATE__` (flat `multimedia_interpolate` section). Field
names map directly:

| Variable | Description |
|---------|------------|
| `LEX_MULTIMEDIA__INTERPOLATE__BACKEND` | Backend selection (`rife`) |
| `LEX_MULTIMEDIA__INTERPOLATE__RIFE_BASE_URL` | RIFE server URL |
| `LEX_MULTIMEDIA__INTERPOLATE__TIMEOUT` | Request timeout in seconds |

Example:

```bash
export LEX_MULTIMEDIA__INTERPOLATE__RIFE_BASE_URL=http://rife.internal:5500
export LEX_MULTIMEDIA__INTERPOLATE__TIMEOUT=45
```

## Advanced Configuration

### Resilience Wrapping

`RifeInterpolationProvider` accepts optional `RetryPolicyProtocol` /
`CircuitBreakerProtocol` instances. Under DI they resolve automatically when
registered in the container, wrapping every `/interpolate` call. Direct
construction works too:

```python
from lexigram.multimedia.interpolate.providers import RifeInterpolationProvider

backend = RifeInterpolationProvider(
    base_url="http://localhost:5500",
    timeout=15.0,
    retry=my_retry_policy,
    circuit_breaker=my_circuit_breaker,
)
```

### Composing with a VideoProcessor

The `VideoInterpolationService` registration is automatic: if the container
has a `VideoProcessor` (from `lexigram-multimedia-video`), the provider
composes `VideoInterpolationService(interpolation_provider, video_processor)`
and registers it. No config keys control this — presence of the protocol in
the container is the only switch:

```python
service = await app.container.resolve(VideoInterpolationService)
result = await service.interpolate_video(asset, factor=2, fps=24.0)
```

### Profile-Based Overlays

```bash
export LEX_PROFILE=production
```

with `application.production.yaml` overriding just the server URL — env vars
still win over the profile file.

## Best Practices

- Keep config minimal — only `rife_base_url` and `timeout` matter in practice.
- Prefer environment variables for per-deployment server URLs (`rife` runs on
  a different host in prod).
- Raise `timeout` for slow GPUs; interpolation of large frames is
  compute-bound, not network-bound.
- Use `InterpolationModule.stub()` in tests (pins the real `rife` backend
  without a live server).