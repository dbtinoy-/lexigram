"""Tests for the TTS reference servers' body caps and f5-tts reference-audio policy (security D4)."""

from __future__ import annotations

from collections.abc import AsyncIterator
import ipaddress
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

pytest.importorskip("aiohttp.test_utils")

_PUBLIC_IP = ipaddress.IPv4Address("93.184.216.34")


@pytest.fixture
async def aiohttp_client() -> AsyncIterator[Any]:
    """Yield a factory that starts a TestClient for the given app."""

    clients: list[TestClient] = []

    async def factory(app: web.Application) -> TestClient:
        client = TestClient(TestServer(app, host="localhost"))
        await client.start_server()
        clients.append(client)
        return client

    yield factory

    for client in clients:
        await client.close()


def test_chatterbox_server_caps_body_at_1_mib() -> None:
    from lexigram.multimedia.tts.servers.chatterbox_server import MAX_BODY_BYTES

    assert MAX_BODY_BYTES == 1 * 1024 * 1024


def test_kokoro_server_caps_body_at_1_mib() -> None:
    from lexigram.multimedia.tts.servers.kokoro_server import MAX_BODY_BYTES

    assert MAX_BODY_BYTES == 1 * 1024 * 1024


def test_piper_server_caps_body_at_1_mib() -> None:
    from lexigram.multimedia.tts.servers.piper_server import MAX_BODY_BYTES

    assert MAX_BODY_BYTES == 1 * 1024 * 1024


def test_f5_tts_server_caps_body_at_64_mib() -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


async def test_f5_reference_audio_fetch_capped(aiohttp_client: Any) -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import _resolve_reference_audio

    async def handler(request: web.Request) -> web.Response:
        return web.Response(
            body=b"\0" * (25 * 1024 * 1024 + 1), content_type="audio/wav"
        )

    app = web.Application()
    app.router.add_get("/ref.wav", handler)
    client = await aiohttp_client(app)

    with pytest.raises(ValueError, match="exceeds"):
        await _resolve_reference_audio(
            str(client.make_url("/ref.wav")), resolver=lambda _: [_PUBLIC_IP]
        )


async def test_f5_reference_audio_fetch_rejects_non_200(aiohttp_client: Any) -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import _resolve_reference_audio

    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=404, body=b"not found")

    app = web.Application()
    app.router.add_get("/missing.wav", handler)
    client = await aiohttp_client(app)

    with pytest.raises(ValueError, match="HTTP 404"):
        await _resolve_reference_audio(
            str(client.make_url("/missing.wav")), resolver=lambda _: [_PUBLIC_IP]
        )


async def test_f5_generate_maps_bad_reference_audio_to_400(
    aiohttp_client: Any,
) -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import handle_generate

    app = web.Application()
    app.router.add_post("/generate", handle_generate)
    client = await aiohttp_client(app)

    resp = await client.post(
        "/generate",
        json={"reference_audio_uri": "http://127.0.0.1:9/missing.wav"},
    )
    assert resp.status == 400


async def test_f5_reference_audio_file_scheme_without_allowlist_root_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import _resolve_reference_audio

    monkeypatch.delenv("F5_TTS_REFERENCE_ROOT", raising=False)

    with pytest.raises(ValueError, match="outside allowed root"):
        await _resolve_reference_audio("file:///etc/passwd")


async def test_f5_reference_audio_file_scheme_allowlisted_root_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import _resolve_reference_audio

    ref_wav = tmp_path / "ref.wav"
    ref_wav.write_bytes(b"RIFF")
    monkeypatch.setenv("F5_TTS_REFERENCE_ROOT", str(tmp_path))

    assert await _resolve_reference_audio(ref_wav.as_uri()) == str(ref_wav)


async def test_f5_reference_audio_file_scheme_sibling_root_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from lexigram.multimedia.tts.servers.f5_tts_server import _resolve_reference_audio

    root = tmp_path / "ref"
    root.mkdir()
    sibling = tmp_path / "ref2"
    sibling.mkdir()
    secret_wav = sibling / "secret.wav"
    secret_wav.write_bytes(b"RIFF")
    monkeypatch.setenv("F5_TTS_REFERENCE_ROOT", str(root))

    # F5_TTS_REFERENCE_ROOT=<tmp>/ref + file://<tmp>/ref2/secret.wav → ValueError
    # (prefix-match escape: sibling dir sharing the root's name prefix)
    with pytest.raises(ValueError, match="outside allowed root"):
        await _resolve_reference_audio(secret_wav.as_uri())
