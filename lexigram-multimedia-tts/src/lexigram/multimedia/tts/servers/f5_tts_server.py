"""Reference F5-TTS server — zero-shot voice cloning from a reference clip.

Run in a dedicated venv with the f5-tts-server extra installed:
  pip install lexigram-multimedia-tts[f5-tts-server]
  lexigram-tts-f5-tts-serve

handle_generate resolves reference_audio_uri itself (HTTP GET or local file
read) — the provider never inlines reference audio bytes into the request.

NOTE: verify F5-TTS's actual inference entrypoint against the installed
package version before relying on this in production (design spec §7,
risk 1).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from aiohttp import web

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    from f5_tts.api import F5TTS  # type: ignore[import-not-found]
    import torch  # type: ignore[import-not-found]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = F5TTS(device=device)


async def _resolve_reference_audio(uri: str) -> str:
    """Return a local filesystem path for the given reference-audio URI."""
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return parsed.path
    if parsed.scheme in ("http", "https"):
        import tempfile

        import aiohttp as _aiohttp

        async with (
            _aiohttp.ClientSession() as session,
            session.get(uri) as resp,
        ):
            data = await resp.read()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(data)
            return f.name
    raise ValueError(f"Unsupported reference_audio_uri scheme: {parsed.scheme!r}")


async def handle_generate(request: web.Request) -> web.Response:
    body = await request.json()
    ref_path = await _resolve_reference_audio(body["reference_audio_uri"])
    wav, sr, _ = _model.infer(
        ref_file=ref_path,
        ref_text=body["reference_text"],
        gen_text=body["text"],
    )

    import io

    import soundfile as sf  # type: ignore[import-not-found]

    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV")
    return web.Response(body=buf.getvalue(), content_type="audio/wav")


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok" if _model is not None else "loading"})


def main() -> None:
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5102)


if __name__ == "__main__":
    main()
