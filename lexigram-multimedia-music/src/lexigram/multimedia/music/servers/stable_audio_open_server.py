"""Reference Stable Audio Open FX/ambience generation server.

Run in a dedicated venv with the stable-audio-open-server extra installed:
  pip install lexigram-multimedia-music[stable-audio-open-server]
  lexigram-music-stable-audio-open-serve

Stable Audio Open has a real native output-length ceiling (commonly
cited around 47 seconds) — this server does not enforce it client-side;
it clamps or rejects at its own discretion (design spec §11.2).

NOTE: verify StableAudioOpenPipeline's constructor/inference signature
against the actually-installed stable-audio-tools version before
relying on this in production (design spec §11.1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

_pipeline: Any = None


async def on_startup(app: web.Application) -> None:
    global _pipeline
    from stable_audio_tools import (  # type: ignore[import-not-found]
        StableAudioOpenPipeline,
    )
    import torch  # type: ignore[import-not-found]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _pipeline = StableAudioOpenPipeline.from_pretrained(device=device)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    audio_bytes = _pipeline.generate(
        prompt=body["prompt"],
        duration_seconds=body.get("duration_seconds", 10.0),
    )
    return web.Response(body=audio_bytes, content_type="audio/wav")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _pipeline is not None else "loading"})


def main() -> None:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5301)


if __name__ == "__main__":
    main()
