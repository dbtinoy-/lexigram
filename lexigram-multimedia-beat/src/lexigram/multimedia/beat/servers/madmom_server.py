"""Reference madmom tempo/beat-detection server.

Run in a dedicated venv with the madmom-server extra installed:
  pip install lexigram-multimedia-beat[madmom-server]
  lexigram-beat-madmom-serve

Loads the model once at process startup; never reloaded per-request.
Verify madmom's actual pinned-version license terms before relying on
this in a commercial deployment (design spec §7/§11.4).
"""

from __future__ import annotations

import base64
import itertools
import tempfile
from typing import Any

from aiohttp import web

_processor: Any = None


async def on_startup(app: web.Application) -> None:
    global _processor
    import madmom

    _processor = madmom.features.beats.RNNBeatProcessor()


async def handle_analyze(request: web.Request) -> web.Response:
    import madmom

    body = await request.json()
    audio_bytes = base64.b64decode(body["audio_bytes"])
    with tempfile.NamedTemporaryFile(suffix=".audio") as f:
        f.write(audio_bytes)
        f.flush()
        activations = _processor(f.name)
        tracker = madmom.features.beats.DBNBeatTrackingProcessor(fps=100)
        beat_timestamps = tracker(activations).tolist()

    tempo_bpm = (
        60.0
        / (
            sum(b2 - b1 for b1, b2 in itertools.pairwise(beat_timestamps))
            / max(len(beat_timestamps) - 1, 1)
        )
        if len(beat_timestamps) > 1
        else 0.0
    )

    return web.json_response(
        {"tempo_bpm": tempo_bpm, "beat_timestamps": beat_timestamps}
    )


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _processor is not None else "loading"})


def main() -> None:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_post("/analyze", handle_analyze)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5600)


if __name__ == "__main__":
    main()
