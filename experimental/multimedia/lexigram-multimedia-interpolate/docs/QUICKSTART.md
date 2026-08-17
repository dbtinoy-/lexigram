# Quickstart

Frame-rate interpolation with `lexigram-multimedia-interpolate` — up and running in minutes.

---

## Install

```bash
uv add lexigram-multimedia-interpolate
```

The package works out of the box as an HTTP client. Only add the extra when
you want to run the bundled RIFE reference server itself (needs PyTorch):

```bash
uv add "lexigram-multimedia-interpolate[rife-server]"
```

---

## Minimal Working Example

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import (
    InterpolationProvider,
    InterpolationRequest,
    MediaAsset,
)
from lexigram.multimedia.interpolate import InterpolationModule


async def main() -> None:
    async with Application.boot(modules=[InterpolationModule.configure()]) as app:
        interpolate: InterpolationProvider = await app.container.resolve(
            InterpolationProvider
        )

        frame_a = MediaAsset(
            mime_type="image/png",
            provider="demo",
            bytes_data=open("frame_a.png", "rb").read(),
        )
        frame_b = MediaAsset(
            mime_type="image/png",
            provider="demo",
            bytes_data=open("frame_b.png", "rb").read(),
        )

        result = await interpolate.interpolate(
            InterpolationRequest(frame_a=frame_a, frame_b=frame_b)
        )

        if result.is_ok():
            mid = result.unwrap()  # synthesized midpoint frame
            with open("midframe.png", "wb") as f:
                f.write(mid.bytes_data)


if __name__ == "__main__":
    asyncio.run(main())
```

Prerequisites: a RIFE server answering `POST /interpolate` (base64 `frame_a_bytes`
+ `frame_b_bytes` → midpoint PNG) at `http://localhost:5500`.

---

## What Just Happened

1. `InterpolationModule.configure()` created a `DynamicModule` wrapping an
   `InterpolationGenerationProvider` and exporting `InterpolationProvider` and
   `InterpolationTask`.
2. During `Application.boot()` the provider's `register()` ran:
   - `InterpolationConfig` was bound in the container as a singleton.
   - `RifeInterpolationProvider` was constructed and registered as the
     `InterpolationProvider` (backend = `"rife"`, default).
   - `InterpolationTask` was wired around the same backend for `lexigram-tasks`
     `submit()` jobs.
   - If the container already had a `VideoProcessor`, a
     `VideoInterpolationService` was composed and registered too.
3. Your call `interpolate(InterpolationRequest(frame_a, frame_b))` posted both
   frames (base64) and received the synthesized midpoint frame as
   `Result[MediaAsset, MultimediaError]`.

---

## Next Steps

- [Guide](./GUIDE.md) — concepts, frame-pair vs video interpolation
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — config keys and env-var overrides