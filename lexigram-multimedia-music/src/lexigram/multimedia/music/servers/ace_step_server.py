"""Reference ACE-Step full-song generation server.

Run in a dedicated venv with the ace-step-server extra installed:
  pip install lexigram-multimedia-music[ace-step-server]
  lexigram-music-ace-step-serve

Loads the model once at process startup; never reloaded per-request.
Empty/absent lyrics produces instrumental-only output — ACE-Step's own
convention, not something this server enforces.

NOTE: ACE-Step is a young, actively-developed project — verify its
Python API's constructor/inference signature against the
actually-installed package version before relying on this in production
(design spec §11.1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

_pipeline: Any = None


async def on_startup(app: web.Application) -> None:
    global _pipeline
    from acestep import AceStepPipeline
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _pipeline = AceStepPipeline.from_pretrained(device=device)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    audio_bytes = _pipeline.generate(
        prompt=body["prompt"],
        duration_seconds=body.get("duration_seconds", 30.0),
        tags=body.get("tags", ""),
        lyrics=body.get("lyrics", ""),
    )
    return web.Response(body=audio_bytes, content_type="audio/wav")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _pipeline is not None else "loading"})


def main() -> None:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5300)


if __name__ == "__main__":
    main()
