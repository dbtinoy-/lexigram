"""Tests for the madmom reference server's decoded-audio length cap and
madmom-optional env-gating (security D4 follow-up).

``madmom`` is not installed in the dev venv, so the handler tests inject a
fake ``madmom`` module (same pattern as the fake-librosa decode-cap tests);
the 503/health tests exercise the env-gated server without any madmom.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import numpy as np
import pytest

from lexigram.contracts.multimedia.security import DEFAULT_MAX_MEDIA_BYTES

pytest.importorskip("aiohttp.test_utils")

_GOOD_AUDIO = base64.b64encode(b"\0" * 4096).decode()


def _fake_madmom() -> ModuleType:
    """Minimal madmom stand-in whose processors return fixed arrays."""
    fake = ModuleType("madmom", "fake madmom for env-gating tests")
    fake.features = ModuleType("madmom.features")
    fake.features.beats = ModuleType("madmom.features.beats")
    processor = MagicMock(return_value=np.zeros(200))
    fake.features.beats.RNNBeatProcessor = MagicMock(return_value=processor)
    tracker = MagicMock(return_value=np.array([0.5, 1.0, 1.5, 2.0]))
    fake.features.beats.DBNBeatTrackingProcessor = MagicMock(return_value=tracker)
    return fake


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


async def test_madmom_analyze_fails_closed_when_madmom_missing(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.beat.servers import madmom_server

    monkeypatch.setattr(madmom_server, "on_startup", _noop_startup)
    monkeypatch.setattr(madmom_server, "_processor", None)
    client = await aiohttp_client(madmom_server.build_app())

    resp = await client.post("/analyze", json={"audio_bytes": _GOOD_AUDIO})

    assert resp.status == 503


async def test_madmom_health_reports_unavailable_when_madmom_missing(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.beat.servers import madmom_server

    monkeypatch.setattr(madmom_server, "on_startup", _noop_startup)
    monkeypatch.setattr(madmom_server, "_processor", None)
    client = await aiohttp_client(madmom_server.build_app())

    resp = await client.get("/health")
    body = await resp.json()

    assert resp.status == 200
    assert body == {"status": "unavailable"}


async def test_madmom_analyze_returns_200_when_madmom_available(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.beat.servers import madmom_server

    monkeypatch.setattr(madmom_server, "_processor", None)
    with patch.dict(sys.modules, {"madmom": _fake_madmom()}):
        client = await aiohttp_client(madmom_server.build_app())
        resp = await client.post("/analyze", json={"audio_bytes": _GOOD_AUDIO})
        body = await resp.json()

    assert resp.status == 200
    assert body["tempo_bpm"] > 0
    assert len(body["beat_timestamps"]) > 1
