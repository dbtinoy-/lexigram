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

import os
from typing import Any
from urllib.parse import urlparse

from aiohttp import web

from lexigram.contracts.multimedia.security import (
    DEFAULT_MAX_MEDIA_BYTES,
    asset_bytes_ok,
)
from lexigram.contracts.security.url_safety import (
    HostResolver,
    is_safe_url_for_request,
)

MAX_BODY_BYTES: int = 64 * 1024 * 1024  # reference-audio base64/JSON window

_model: Any = None


async def on_startup(app: web.Application) -> None:
    global _model
    from f5_tts.api import F5TTS  # type: ignore[import-not-found]
    import torch  # type: ignore[import-not-found]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = F5TTS(device=device)


async def _resolve_reference_audio(
    uri: str, *, resolver: HostResolver | None = None
) -> str:
    """Return a local filesystem path for the given reference-audio URI.

    file:// URIs must point inside ``F5_TTS_REFERENCE_ROOT`` when that
    environment variable is set; http(s) URIs are URL-safety checked,
    fetched without redirects, and capped at the framework media size.

    Args:
        uri: Reference-audio URI (file://, http:// or https://).
        resolver: Optional hostname resolver for the URL-safety check.
            Defaults to the system resolver.

    Returns:
        A local path for the resolved audio file.

    Raises:
        ValueError: If the URI scheme is unsupported, the file path is
            outside the allowed root, or the payload exceeds the cap.
    """
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        root = os.environ.get("F5_TTS_REFERENCE_ROOT", "")
        if root:
            base = os.path.realpath(root)
            real = os.path.realpath(parsed.path)
            allowed = real == base or real.startswith(base.rstrip(os.sep) + os.sep)
        else:
            allowed = False
        if not allowed:
            raise ValueError(
                f"reference_audio_uri outside allowed root: {parsed.path!r}"
            )
        return parsed.path
    if parsed.scheme in ("http", "https"):
        if not is_safe_url_for_request(uri, resolver=resolver):
            raise ValueError(f"unsafe reference_audio_uri: {uri!r}")
        import tempfile

        import aiohttp as _aiohttp

        async with (
            _aiohttp.ClientSession() as session,
            session.get(uri, allow_redirects=False) as resp,
        ):
            declared = resp.content_length
            if declared is not None and not asset_bytes_ok(
                declared, max_bytes=DEFAULT_MAX_MEDIA_BYTES
            ):
                raise ValueError(
                    f"reference_audio_uri body exceeds media cap: {declared} bytes"
                )
            chunks = []
            total = 0
            async for chunk in resp.content.iter_chunked(64 * 1024):
                total += len(chunk)
                if not asset_bytes_ok(total, max_bytes=DEFAULT_MAX_MEDIA_BYTES):
                    raise ValueError(
                        f"reference_audio_uri body exceeds media cap: {total} bytes"
                    )
                chunks.append(chunk)
            data = b"".join(chunks)
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
    app = web.Application(client_max_size=MAX_BODY_BYTES)
    app.on_startup.append(on_startup)
    app.router.add_post("/generate", handle_generate)
    app.router.add_get("/health", handle_health)
    web.run_app(app, port=5102)


if __name__ == "__main__":
    main()
