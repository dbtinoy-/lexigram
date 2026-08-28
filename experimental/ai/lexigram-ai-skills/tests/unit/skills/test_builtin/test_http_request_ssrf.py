"""SSRF-guard tests for the agent HTTPRequestSkill (round-5 finding).

The skill fetches arbitrary URLs on behalf of an agent; it previously had
no private/reserved-address protection, so an agent (or prompt-injected
content driving one) could reach the cloud metadata endpoint
(169.254.169.254), loopback services, and internal networks — and read
their responses.  It now consults ``is_safe_url_for_request`` before
requesting and validates every redirect target via a guarded urllib
redirect handler.
"""

from __future__ import annotations

from typing import Any, Self
from unittest.mock import MagicMock
import urllib.error
import urllib.request

import pytest

from lexigram.ai.skills.builtin.http_request import (
    HTTPRequestSkill,
    _SafeRedirectHandler,
)


class _FakeResponse:
    status = 200

    def read(self) -> bytes:
        return b"hello"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class _FakeOpener:
    def open(self, req: Any, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse()


@pytest.mark.asyncio
async def test_rejects_loopback_url(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = HTTPRequestSkill()
    result = await skill.execute(url="http://127.0.0.1:8000/admin", method="GET")
    assert result.is_err()
    assert "SSRF" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_rejects_cloud_metadata_url(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = HTTPRequestSkill()
    result = await skill.execute(
        url="http://169.254.169.254/latest/meta-data/", method="GET"
    )
    assert result.is_err()
    assert "SSRF" in str(result.unwrap_err())


@pytest.mark.asyncio
async def test_rejects_link_local_url(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = HTTPRequestSkill()
    result = await skill.execute(url="http://169.254.170.2/credentials", method="GET")
    assert result.is_err()


@pytest.mark.asyncio
async def test_guard_consulted_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = HTTPRequestSkill()
    monkeypatch.setattr(
        "lexigram.ai.skills.builtin.http_request.is_safe_url_for_request",
        lambda _url: False,
    )
    opener = MagicMock()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_a: opener)
    result = await skill.execute(url="http://example.com/x", method="GET")
    assert result.is_err()
    opener.open.assert_not_called()


@pytest.mark.asyncio
async def test_public_url_reaches_opener(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = HTTPRequestSkill()
    monkeypatch.setattr(
        "lexigram.ai.skills.builtin.http_request.is_safe_url_for_request",
        lambda _url: True,
    )
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_a: _FakeOpener())
    result = await skill.execute(url="https://example.com/x", method="GET")
    assert result.is_ok()
    output = result.unwrap().output
    assert output["status_code"] == 200
    assert output["body"] == "hello"


# --- guarded redirect handler ---


def test_redirect_handler_rejects_private_target() -> None:
    handler = _SafeRedirectHandler()
    req = urllib.request.Request("http://example.com/start")
    with pytest.raises(urllib.error.URLError):
        handler.redirect_request(
            req, None, 302, "Found", {}, "http://169.254.169.254/latest"
        )


def test_redirect_handler_rejects_loopback_target() -> None:
    handler = _SafeRedirectHandler()
    req = urllib.request.Request("http://example.com/start")
    with pytest.raises(urllib.error.URLError):
        handler.redirect_request(req, None, 301, "Moved", {}, "http://127.0.0.1:8080")


def test_redirect_handler_allows_public_target(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = _SafeRedirectHandler()
    req = urllib.request.Request("http://example.com/start")
    redirected = handler.redirect_request(
        req, None, 302, "Found", {}, "https://example.com/next"
    )
    assert isinstance(redirected, urllib.request.Request)
    assert redirected.full_url == "https://example.com/next"
