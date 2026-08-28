"""Reference madmom tempo/beat-detection server.

Run in a dedicated venv with the madmom-server extra installed:
  pip install lexigram-multimedia-beat[madmom-server]
  lexigram-beat-madmom-serve

Loads the model once at process startup; never reloaded per-request.
Verify madmom's actual pinned-version license terms before relying on
this in a commercial deployment (design spec §7/§11.4).

madmom is an optional extra: if it is not installed, the server still
starts and serves /health, but /analyze returns HTTP 503 (fail-closed)
until the process runs in a madmom-enabled environment.
"""

from __future__ import annotations

import base64
import itertools
import tempfile
from typing import Any

from aiohttp import web

from lexigram.contracts.multimedia.security import DEFAULT_MAX_MEDIA_BYTES
from lexigram.logging import get_logger

MAX_BODY_BYTES: int = 64 * 1024 * 1024  # media payloads, base64 window
MAX_AUDIO_BYTES: int = DEFAULT_MAX_MEDIA_BYTES  # decoded-length cap (contracts policy)

logger = get_logger(__name__)

_processor: Any = None


async def on_startup(app: web.Application) -> None:
    global _processor
    try:
        import madmom
    except ImportError:
        logger.warning(
            "madmom_unavailable",
            detail="reference server running without the madmom optional extra",
        )
        return
    _processor = madmom.features.beats.RNNBeatProcessor()


async def handle_analyze(request: web.Request) -> web.Response:
    body = await request.json()
    raw_audio = body.get("audio_bytes")
    if not isinstance(raw_audio, str):
        raise web.HTTPBadRequest(text="audio_bytes must be a base64 string")
    audio_bytes = base64.b64decode(raw_audio)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise web.HTTPBadRequest(text=f"decoded audio exceeds {MAX_AUDIO_BYTES} bytes")

    if _processor is None:
        raise web.HTTPServiceUnavailable(text="madmom processor unavailable")

    import madmom

    with tempfile.NamedTemporaryFile(suffix=".audio") as f:
        f.write(audio_bytes)
        f.flush()
        activations = _processor(f.name)
        tracker = madmom.features.beats.DBNBeatTrackingProcessor(fps=100)
        beat_timestamps = tracker(activations).tolist()

    tempo_bpm = 0.0
    if len(beat_timestamps) > 1:
        intervals = [b2 - b1 for b1, b2 in itertools.pairwise(beat_timestamps)]
        mean_interval = sum(intervals) / len(intervals)
        if mean_interval > 0:
            tempo_bpm = 60.0 / mean_interval

    return web.json_response(
        {"tempo_bpm": tempo_bpm, "beat_timestamps": beat_timestamps}
    )


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response(
        {"status": "ok" if _processor is not None else "unavailable"}
    )


def build_app() -> web.Application:
    """Build the reference server application with its explicit body cap."""

    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/analyze", handle_analyze)
    app.router.add_get("/health", handle_health)
    return app


def main() -> None:
    # Loopback only: /analyze is unauthenticated and runs CPU-heavy
    # processing, so the reference server must not be reachable from
    # other hosts by default.  Deployments needing remote access should
    # front it with an authenticated reverse proxy and bind explicitly.
    web.run_app(build_app(), host="127.0.0.1", port=5600)


if __name__ == "__main__":
    main()
