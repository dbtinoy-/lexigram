"""Reference Kokoro-82M TTS server.

Run in a dedicated venv with the kokoro-server extra installed:
  pip install lexigram-multimedia-tts[kokoro-server]
  lexigram-tts-kokoro-serve

NOTE: verify KPipeline/KModel's constructor and inference call signature
against the actually-installed kokoro package version before relying on
this in production (design spec §7, risk 1).
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 1 * 1024 * 1024  # text-only endpoint

_pipeline: Any = None


async def on_startup(app: web.Application) -> None:
    global _pipeline
    from kokoro import KPipeline  # type: ignore[import-not-found]

    _pipeline = KPipeline(lang_code="a")


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    voice = body.get("voice", "af_heart")
    generator = _pipeline(body["text"], voice=voice)
    audio_chunks = [audio for _, _, audio in generator]

    import io

    import numpy as np
    import soundfile as sf  # type: ignore[import-not-found]

    audio = np.concatenate(audio_chunks)
    buf = io.BytesIO()
    sf.write(buf, audio, 24000, format="WAV")
    return web.Response(body=buf.getvalue(), content_type="audio/wav")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _pipeline is not None else "loading"})


def main() -> None:
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5101)


if __name__ == "__main__":
    main()
