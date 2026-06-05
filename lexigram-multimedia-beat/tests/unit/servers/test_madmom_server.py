"""Tests for the madmom reference server's decoded-audio length cap (security D4)."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

from lexigram.contracts.multimedia.security import DEFAULT_MAX_MEDIA_BYTES

pytest.importorskip("aiohttp.test_utils")


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


async def _noop_startup(app: web.Application) -> None:
    pass


def test_madmom_server_caps_body_size() -> None:
    from lexigram.multimedia.beat.servers.madmom_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


async def test_madmom_rejects_oversized_decoded_audio(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.beat.servers import madmom_server

    monkeypatch.setattr(madmom_server, "on_startup", _noop_startup)
    client = await aiohttp_client(madmom_server.build_app())

    oversized = base64.b64encode(b"\0" * (DEFAULT_MAX_MEDIA_BYTES + 1)).decode()
    resp = await client.post("/analyze", json={"audio_bytes": oversized})

    assert resp.status == 400


async def test_madmom_rejects_non_string_audio_bytes(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.beat.servers import madmom_server

    monkeypatch.setattr(madmom_server, "on_startup", _noop_startup)
    client = await aiohttp_client(madmom_server.build_app())

    resp = await client.post("/analyze", json={"audio_bytes": 12345})

    assert resp.status == 400