"""Reference Piper TTS server — ONNX, CPU-only, no GPU device branch needed.

Run in a dedicated venv with the piper-server extra installed:
  pip install lexigram-multimedia-tts[piper-server]
  lexigram-tts-piper-serve

Unlike chatterbox/kokoro/f5-tts, on_startup has no torch.cuda.is_available()
branch — Piper's onnxruntime backend is CPU-only by design (design spec §7).

NOTE: verify PiperVoice.load/.synthesize's actual signature against the
installed piper-tts package version before relying on this in production.
"""

from __future__ import annotations

from typing import Any

from aiohttp import web

MAX_BODY_BYTES: int = 1 * 1024 * 1024  # text-only endpoint

_voice: Any = None

_DEFAULT_MODEL_PATH = "en_US-lessac-medium.onnx"


async def on_startup(app: web.Application) -> None:
    global _voice
    from piper import PiperVoice  # type: ignore[import-not-found]

    _voice = PiperVoice.load(_DEFAULT_MODEL_PATH)


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()

    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        _voice.synthesize(body["text"], wav_file)
    return web.Response(body=buf.getvalue(), content_type="audio/wav")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _voice is not None else "loading"})


def main() -> None:
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5103)


if __name__ == "__main__":
    main()
