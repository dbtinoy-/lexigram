"""Tests for the upscale reference servers' body caps and scale_factor validation (security D4)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

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


class _FakeUpscaler:
    def upscale(self, image_bytes: bytes, *, scale_factor: int) -> bytes:
        return b"upscaled-png"


def test_hat_server_app_sets_client_max_size() -> None:
    from lexigram.multimedia.upscale.servers.hat_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


def test_real_esrgan_server_app_sets_client_max_size() -> None:
    from lexigram.multimedia.upscale.servers.real_esrgan_server import MAX_BODY_BYTES

    assert isinstance(MAX_BODY_BYTES, int) and MAX_BODY_BYTES >= 64 * 1024 * 1024


async def test_hat_server_rejects_scale_factor_outside_2_4(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.upscale.servers import hat_server

    monkeypatch.setattr(hat_server, "on_startup", _noop_startup)
    client = await aiohttp_client(hat_server.build_app())

    resp = await client.post(
        "/upscale", json={"image_bytes": "aGVsbG8=", "scale_factor": 3}
    )

    assert resp.status == 400


@pytest.mark.parametrize("scale_factor", [2, 4])
async def test_hat_server_accepts_scale_factor_2_and_4(
    aiohttp_client: Any,
    monkeypatch: pytest.MonkeyPatch,
    scale_factor: int,
) -> None:
    from lexigram.multimedia.upscale.servers import hat_server

    monkeypatch.setattr(hat_server, "on_startup", _noop_startup)
    monkeypatch.setattr(hat_server, "_model", _FakeUpscaler())
    client = await aiohttp_client(hat_server.build_app())

    resp = await client.post(
        "/upscale",
        json={"image_bytes": "aGVsbG8=", "scale_factor": scale_factor},
    )

    assert resp.status == 200
    assert resp.headers["Content-Type"] == "image/png"


async def test_real_esrgan_server_rejects_scale_factor_outside_2_4(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.upscale.servers import real_esrgan_server

    monkeypatch.setattr(real_esrgan_server, "on_startup", _noop_startup)
    client = await aiohttp_client(real_esrgan_server.build_app())

    resp = await client.post(
        "/upscale", json={"image_bytes": "aGVsbG8=", "scale_factor": 3}
    )

    assert resp.status == 400


async def test_real_esrgan_server_accepts_scale_factor_2(
    aiohttp_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lexigram.multimedia.upscale.servers import real_esrgan_server

    monkeypatch.setattr(real_esrgan_server, "on_startup", _noop_startup)
    monkeypatch.setattr(real_esrgan_server, "_model", _FakeUpscaler())
    client = await aiohttp_client(real_esrgan_server.build_app())

    resp = await client.post(
        "/upscale",
        json={"image_bytes": "aGVsbG8=", "scale_factor": 2},
    )

    assert resp.status == 200
    assert resp.headers["Content-Type"] == "image/png"
