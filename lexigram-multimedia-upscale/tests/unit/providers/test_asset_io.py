"""Tests for guarded remote-asset resolution (security F1)."""

from __future__ import annotations

import ipaddress
from typing import Self

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

from lexigram.contracts.multimedia.types import MediaAsset
from lexigram.multimedia.upscale.providers._asset_io import resolve_asset_bytes

_PUBLIC_IP = ipaddress.IPv4Address("93.184.216.34")


class _FakeContent:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def iter_chunked(self, chunk_size: int):
        for chunk in self._chunks:
            yield chunk


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self.content = _FakeContent([body] if body else [])
        self.content_length: int | None = len(body) if body else None


class _RespContext:
    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp

    async def __aenter__(self) -> _FakeResp:
        return self._resp

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeSession:
    def __init__(self, resp: _FakeResp) -> None:
        self._resp = resp
        self.get_kwargs: dict[str, object] = {}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def get(self, url: str, **kwargs: object) -> _RespContext:
        self.get_kwargs = kwargs
        return _RespContext(self._resp)


class TestResolveAssetBytesSchemeAndIpPolicy:
    async def test_file_scheme_rejected(self) -> None:
        with pytest.raises(ValueError):
            await resolve_asset_bytes(
                MediaAsset(
                    mime_type="image/png", provider="x", uri="file:///etc/passwd"
                )
            )

    async def test_private_literal_ip_rejected(self) -> None:
        with pytest.raises(ValueError):
            await resolve_asset_bytes(
                MediaAsset(
                    mime_type="image/png", provider="x", uri="http://127.0.0.1:9/x.png"
                ),
                resolver=lambda _: [_PUBLIC_IP],
            )

    async def test_public_dns_allowed_via_injected_resolver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        session = _FakeSession(_FakeResp(body=b"png-bytes"))
        monkeypatch.setattr(aiohttp, "ClientSession", lambda: session)

        result = await resolve_asset_bytes(
            MediaAsset(
                mime_type="image/png", provider="x", uri="http://example.com/x.png"
            ),
            resolver=lambda _: [_PUBLIC_IP],
        )

        assert result == b"png-bytes"
        assert session.get_kwargs.get("allow_redirects") is False


class TestResolveAssetBytesSizeCap:
    async def test_oversized_body_rejected(self) -> None:
        async def handler(request):
            return web.Response(
                body=b"\0" * (25 * 1024 * 1024 + 1), content_type="image/png"
            )

        app = web.Application()
        app.router.add_get("/big.png", handler)
        async with TestClient(
            TestServer(app, host="localhost"), raise_for_status=False
        ) as client:
            asset = MediaAsset(
                mime_type="image/png",
                provider="x",
                uri=str(client.make_url("/big.png")),
            )
            with pytest.raises(ValueError, match="too large"):
                # NOTE: the file:// and literal-IP branches are covered above or
                # via the injected resolver; this test hits http(s).
                await resolve_asset_bytes(asset, resolver=lambda _: [_PUBLIC_IP])

    async def test_unsized_streaming_body_rejected(self) -> None:
        async def handler(request):
            resp = web.StreamResponse()
            await resp.prepare(request)
            await resp.write(b"\0" * (25 * 1024 * 1024 + 1))
            await resp.write_eof()
            return resp

        app = web.Application()
        app.router.add_get("/big.bin", handler)
        async with TestClient(
            TestServer(app, host="localhost"), raise_for_status=False
        ) as client:
            asset = MediaAsset(
                mime_type="image/png",
                provider="x",
                uri=str(client.make_url("/big.bin")),
            )
            with pytest.raises(ValueError, match="too large"):
                await resolve_asset_bytes(asset, resolver=lambda _: [_PUBLIC_IP])
