"""Reference Chatterbox TTS server.

Run in a dedicated venv with the chatterbox-server extra installed:
  pip install lexigram-multimedia-tts[chatterbox-server]
  lexigram-tts-chatterbox-serve

Loads the model once at process startup; never reloaded per-request.

NOTE: Chatterbox is under active development — verify ChatterboxTTS's
constructor/generate signature against the actually-installed package
version before relying on this in production (design spec §7, risk 1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 1 * 1024 * 1024  # text-only endpoint

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    from chatterbox.tts import ChatterboxTTS
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = ChatterboxTTS.from_pretrained(device=device)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    wav = _model.generate(
        body["text"],
        exaggeration=body.get("exaggeration", 0.5),
        cfg_weight=body.get("cfg_weight", 0.5),
        temperature=body.get("temperature", 0.85),
    )
    import io

    import torchaudio

    buf = io.BytesIO()
    torchaudio.save(buf, wav, _model.sr, format="wav")
    return web.Response(body=buf.getvalue(), content_type="audio/wav")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _model is not None else "loading"})


def main() -> None:
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5100)


if __name__ == "__main__":
    main()
