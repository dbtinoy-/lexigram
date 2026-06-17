# How-To Guides: lexigram-multimedia-music

Task-oriented recipes for common music generation operations. All identifiers come from the package source — `src/lexigram/multimedia/music/`.

---

## Generate a Track with the Default Backend

Use `AudioMusicModule.configure()` with no arguments — the `local-http` backend at `http://localhost:5003` is selected (see `MusicConfig.backend`'s default).

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
        music: MusicProvider = await app.container.resolve(MusicProvider)
        result = await music.generate(
            MusicRequest(prompt="calm lo-fi beats, 85 bpm", duration_seconds=30.0)
        )
        if result.is_ok():
            asset = result.unwrap()
            assert asset.has_bytes
            with open("track.mp3", "wb") as f:
                f.write(asset.bytes_data)  # type: ignore[arg-type]


asyncio.run(main())
```

---

## Switch to the ACE-Step Backend (Vocals or Instrumental)

ACE-Step generates full songs with optional vocals. Configure it via `MusicConfig`:

```python
from lexigram.multimedia.music import AudioMusicModule
from lexigram.multimedia.music.config import MusicConfig

module = AudioMusicModule.configure(
    config=MusicConfig(backend="ace-step", ace_step_base_url="http://localhost:5300")
)
```

Start the reference server in a dedicated venv:

```bash
pip install "lexigram-multimedia-music[ace-step-server]"
lexigram-music-ace-step-serve          # loads AceStepPipeline once, serves :5300
```

Request vocals by passing lyrics through `extra`; omit them for instrumental-only:

```python
request = MusicRequest(
    prompt="upbeat synthwave",
    duration_seconds=90.0,
    extra={"tags": "synthwave, driving", "lyrics": "Neon skyline, we drive all night"},
)
```

`AceStepMusicProvider.generate()` maps `extra["tags"]` and `extra["lyrics"]` onto the request payload sent to `/generate`.

---

## Use Stable Audio Open for Short FX / Ambience

Stable Audio Open is a straight text-to-audio model — `request.extra` is **not read** (`StableAudioOpenMusicProvider` ignores it) and output is a native short window, so keep `duration_seconds` modest.

```python
config = MusicConfig(
    backend="stable-audio-open",
    stable_audio_open_base_url="http://localhost:5301",
    timeout=45.0,  # provider default is already 45s for this backend
)
```

```bash
pip install "lexigram-multimedia-music[stable-audio-open-server]"
lexigram-music-stable-audio-open-serve    # serves :5301
```

```python
result = await music.generate(
    MusicRequest(prompt="soft rain on a window, low-fi", duration_seconds=10.0)
)
```

---

## Submit Generation as a Background Job

`MusicGenerationTask` is already bound to the same backend instance the provider registered. `run()` returns a JSON-serializable dict — safe for `lexigram-tasks`' result store.

```python
task: MusicGenerationTask = await app.container.resolve(MusicGenerationTask)
job_result = await task.run(
    {
        "prompt": "heroic trailer music",
        "duration_seconds": 20.0,
        "format": "mp3",
        "extra": {"tags": "epic, orchestral"},
    }
)
print(job_result["provider"], job_result["mime_type"])
```

Unhappy path: when `backend.generate()` returns `Err`, `run()` **raises** `result.unwrap_err()` — the task is marked failed, which lexigram-tasks can retry.

---

## Run Music Generation in Tests (No Network)

`AudioMusicModule.stub()` still builds the real provider but is pinned to the default `local-http` backend — no API keys, no config file:

```python
import asyncio

from lexigram import Application
from lexigram.multimedia.music import AudioMusicModule


async def test_boot():
    async with Application.boot(modules=[AudioMusicModule.stub()]) as app:
        assert app.container is not None
```

For hermetic unit tests, mock the backend protocol instead of hitting any HTTP endpoint:

```python
from unittest.mock import AsyncMock
from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.music.tasks import MusicGenerationTask


def test_task_shape() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/wav", provider="ace-step", bytes_data=b"x")
    )
    task = MusicGenerationTask(backend=backend)
    # ... await task.run({"prompt": "x", "duration_seconds": 30.0, "format": "wav"})
```

---

## Check Provider Health Before Generating

`AudioMusicProvider.health_check()` pings the configured backend's `/health` endpoint. It needs a provider-style call, which `Application` exposes via the health subsystem — or call it directly for a quick liveness probe:

```python
await provider.health_check(timeout=5.0)
# -> HealthCheckResult(
#      component="music",
#      status=HealthStatus.HEALTHY | HealthStatus.DEGRADED | HealthStatus.UNHEALTHY,
#    )
```

- `HEALTHY` — `/health` returned 200.
- `DEGRADED` — server reachable but non-200, or connection refused / timeout / `aiohttp.ClientError`.
- `UNHEALTHY` — the provider holds no backend (registration never happened).

---

## Notes

- **Error handling is `Result`-based** — every provider maps transport failures (`aiohttp.ClientError`, `TimeoutError`) and non-200 responses into `Err(MusicGenerationError(...))`; nothing raises except `register()`-time `ProviderNotInstalledError` for unimplemented backends.
- **`format` is advisory** — the reference servers return native bytes (typically WAV) regardless; `LocalHttpMusicProvider` trusts the server's `Content-Type` (defaulting to `audio/mpeg`).
- **URLs are `rstrip("/")`-ed** by every backend — trailing slashes are harmless.
- **Extra knobs**: only `AceStepMusicProvider` consumes `request.extra` (`tags`, `lyrics`) today.