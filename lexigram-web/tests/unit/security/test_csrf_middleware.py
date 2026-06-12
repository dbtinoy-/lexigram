"""Tests for the CSRFProtectionMiddleware.

Adapted from lexigram-security test suite; imports updated to
lexigram.web.security.* after HTTP middleware absorption in Task 3.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock

import pytest

from lexigram.result import Ok
from lexigram.web.security.config import CSRFConfig
from lexigram.web.security.csrf.middleware import CSRFProtectionMiddleware

#: Any placeholder token value (unverifiable without a signing secret).
_RAW_TOKEN = "test-token-abc123"

#: Shared signing secret for verifiable-token tests.
_TEST_SECRET = "test-secret-key-32-bytes-long!!"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scope(
    method: str = "GET",
    path: str = "/",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
    }


def _cookie_header(pairs: dict[str, str]) -> tuple[bytes, bytes]:
    cookie_str = "; ".join(f"{k}={v}" for k, v in pairs.items())
    return (b"cookie", cookie_str.encode())


def _make_app(*, called: list[bool] | None = None) -> AsyncMock:
    """Return a no-op ASGI app that records whether it was called."""
    store: list[bool] = called if called is not None else []

    async def _app(scope: Any, receive: Any, send: Any) -> None:  # noqa: ARG001
        store.append(True)

    return _app  # type: ignore[return-value]


async def _run(
    middleware: CSRFProtectionMiddleware, scope: dict[str, Any]
) -> list[dict[str, Any]]:
    """Run the middleware and collect sent messages."""
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.disconnect"}

    async def send(msg: dict[str, Any]) -> None:
        messages.append(msg)

    await middleware(scope, receive, send)
    return messages


# ---------------------------------------------------------------------------
# Non-HTTP passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_http_scope_passes_through() -> None:
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app)
    scope = {"type": "websocket", "path": "/ws"}
    await _run(middleware, scope)
    assert inner_called


# ---------------------------------------------------------------------------
# Excluded paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_excluded_path_skips_validation_on_post() -> None:
    config = CSRFConfig(excluded_paths=["/api/"])
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(method="POST", path="/api/data")
    await _run(middleware, scope)
    assert inner_called, "Excluded path should bypass CSRF validation"


@pytest.mark.asyncio
async def test_non_excluded_post_without_token_returns_403() -> None:
    config = CSRFConfig(excluded_paths=["/api/"])
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(method="POST", path="/form")
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


# ---------------------------------------------------------------------------
# Cookie-aware excluded paths (F-W2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_excluded_path_with_cookie_still_validates() -> None:
    """Excluded-path bypass applies to cookie-less clients; cookie-bearing
    requests on excluded paths are validated."""
    config = CSRFConfig(
        excluded_paths=["/api/"],
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
    )
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        path="/api/data",
        headers=[_cookie_header({"csrf_token": "tok"})],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


@pytest.mark.asyncio
async def test_excluded_path_with_cookie_and_matching_token_passes() -> None:
    """Cookie-bearing excluded-path requests pass when tokens match."""
    config = CSRFConfig(
        excluded_paths=["/api/"],
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
    )
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    token = middleware._build_signed_token(int(time.time()))
    assert token is not None
    scope = _make_scope(
        method="POST",
        path="/api/data",
        headers=[
            _cookie_header({"csrf_token": token}),
            (b"x-csrf-token", token.encode()),
        ],
    )
    await _run(middleware, scope)
    assert inner_called


@pytest.mark.asyncio
async def test_excluded_path_with_cookie_json_content_type_passes() -> None:
    """JSON clients keep their bypass on excluded paths even with cookies."""
    config = CSRFConfig(
        excluded_paths=["/api/"],
        exclude_content_types=["application/json"],
    )
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        path="/api/data",
        headers=[
            _cookie_header({"csrf_token": "tok"}),
            (b"content-type", b"application/json"),
        ],
    )
    await _run(middleware, scope)
    assert inner_called


@pytest.mark.asyncio
async def test_excluded_safe_method_with_cookie_passes() -> None:
    """Safe methods on excluded paths pass through regardless of cookies."""
    config = CSRFConfig(excluded_paths=["/api/"], cookie_name="csrf_token")
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="GET",
        path="/api/data",
        headers=[_cookie_header({"csrf_token": "tok"})],
    )
    await _run(middleware, scope)
    assert inner_called


# ---------------------------------------------------------------------------
# Content-type exclusion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_json_content_type_skips_csrf_validation() -> None:
    config = CSRFConfig(exclude_content_types=["application/json"])
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        headers=[(b"content-type", b"application/json")],
    )
    await _run(middleware, scope)
    assert inner_called, "JSON requests should bypass CSRF validation"


@pytest.mark.asyncio
async def test_form_post_without_token_returns_403() -> None:
    config = CSRFConfig()
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        headers=[(b"content-type", b"application/x-www-form-urlencoded")],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


# ---------------------------------------------------------------------------
# Auth scheme exclusion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bearer_auth_skips_csrf_validation() -> None:
    config = CSRFConfig(exclude_auth_schemes=["bearer"])
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        headers=[(b"authorization", b"Bearer token123")],
    )
    await _run(middleware, scope)
    assert inner_called, "Bearer auth requests should bypass CSRF validation"


# ---------------------------------------------------------------------------
# Safe methods issue token cookie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_without_csrf_cookie_sets_cookie() -> None:
    config = CSRFConfig(cookie_name="csrf_token")

    # App must actually send a response so the CSRF cookie injection fires
    async def _responding_app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = CSRFProtectionMiddleware(_responding_app, config=config)

    scope = _make_scope(method="GET")
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    headers_list = start.get("headers", [])
    header_names = {name for name, _ in headers_list}
    # Should have set a CSRF cookie
    assert b"set-cookie" in header_names, "GET without cookie should set a CSRF cookie"


# ---------------------------------------------------------------------------
# Double-submit cookie validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_with_matching_signed_tokens_passes() -> None:
    """POST with a valid signed cookie and the matching header passes."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
    )
    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config)

    token = middleware._build_signed_token(int(time.time()))
    assert token is not None
    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": token}),
            (b"x-csrf-token", token.encode()),
        ],
    )
    await _run(middleware, scope)
    assert inner_called, "POST with matching signed CSRF cookie and header should pass"


@pytest.mark.asyncio
async def test_post_without_secret_fails_closed() -> None:
    """Without a signing secret even matching raw tokens are rejected."""
    config = CSRFConfig(cookie_name="csrf_token", header_name="X-CSRF-Token")
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": _RAW_TOKEN}),
            (b"x-csrf-token", _RAW_TOKEN.encode()),
        ],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


@pytest.mark.asyncio
async def test_post_with_stale_signed_token_rejected() -> None:
    """Expired signed tokens are rejected on unsafe methods."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
        token_ttl=600,
    )
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    stale_ts = int(time.time()) - 601
    token = middleware._build_signed_token(stale_ts)
    assert token is not None
    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": token}),
            (b"x-csrf-token", token.encode()),
        ],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


@pytest.mark.asyncio
async def test_post_with_tampered_signature_rejected() -> None:
    """A valid payload with a forged signature is rejected."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
    )
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    token = middleware._build_signed_token(int(time.time()))
    assert token is not None
    payload, _sig = token.rsplit(".", 1)
    forged = f"{payload}.{_sig[:-1]}A"
    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": forged}),
            (b"x-csrf-token", forged.encode()),
        ],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


@pytest.mark.asyncio
async def test_post_with_unparseable_token_rejected() -> None:
    """Malformed token shapes (no signature) are rejected."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
    )
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": _RAW_TOKEN}),
            (b"x-csrf-token", _RAW_TOKEN.encode()),
        ],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


@pytest.mark.asyncio
async def test_post_with_mismatched_tokens_returns_403() -> None:
    """A valid cookie with a different header value is rejected."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
    )
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config)

    token = middleware._build_signed_token(int(time.time()))
    assert token is not None
    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": token}),
            (b"x-csrf-token", b"different-header-token"),
        ],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403


# ---------------------------------------------------------------------------
# Signed token issuance & rotation (cookie mode)
# ---------------------------------------------------------------------------


async def _responding_app(scope: Any, receive: Any, send: Any) -> None:  # noqa: ARG001
    """Minimal app that emits a 200 response so Set-Cookie can fire."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def _signed_cookie_pairs(messages: list[dict[str, Any]]) -> dict[str, str]:
    """Parse Set-Cookie headers from the sent response messages."""
    pairs: dict[str, str] = {}
    for msg in messages:
        for name, value in msg.get("headers", []):
            if name == b"set-cookie":
                pairs.setdefault("set-cookie", value.decode())
    return pairs


@pytest.mark.asyncio
async def test_get_without_cookie_sets_cookie() -> None:
    """GET without a CSRF cookie issues one (random fallback without a secret)."""
    config = CSRFConfig(cookie_name="csrf_token")
    middleware = CSRFProtectionMiddleware(_responding_app, config=config)

    scope = _make_scope(method="GET")
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    header_names = {name for name, _ in start.get("headers", [])}
    assert b"set-cookie" in header_names, "GET without cookie should set a CSRF cookie"


@pytest.mark.asyncio
async def test_get_with_secret_sets_signed_token() -> None:
    """With a secret, a fresh signed token is issued and exposed in the header."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
    )
    middleware = CSRFProtectionMiddleware(_responding_app, config=config)

    scope = _make_scope(method="GET")
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    headers = dict(start.get("headers", []))
    cookie = headers.get(b"set-cookie", b"").decode()
    assert cookie.startswith("csrf_token=")
    issued = cookie.split("=", 1)[1].split(";", 1)[0]
    assert "." in issued, "issued token must be signed (payload.signature)"

    header_token = headers.get(b"x-csrf-token", b"").decode()
    assert header_token == issued, "SPA must be able to read the issued token"

    parsed = middleware._parse_token(issued)
    assert parsed is not None


@pytest.mark.asyncio
async def test_get_with_fresh_cookie_does_not_rotate() -> None:
    """A fresh valid cookie is reused — no Set-Cookie on the response."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
        token_ttl=3600,
    )
    middleware = CSRFProtectionMiddleware(_responding_app, config=config)
    token = middleware._build_signed_token(int(time.time()))
    assert token is not None

    scope = _make_scope(
        method="GET",
        headers=[_cookie_header({"csrf_token": token})],
    )
    messages = await _run(middleware, scope)
    pairs = _signed_cookie_pairs(messages)
    assert "set-cookie" not in pairs, "fresh token must not be rotated"
    start = next(m for m in messages if m.get("type") == "http.response.start")
    headers = dict(start.get("headers", []))
    assert headers.get(b"x-csrf-token", b"").decode() == token


@pytest.mark.asyncio
async def test_get_with_stale_cookie_rotates_token() -> None:
    """A stale signed cookie is rotated on the next safe method."""
    config = CSRFConfig(
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        secret_key=_TEST_SECRET,
        token_ttl=600,
    )
    middleware = CSRFProtectionMiddleware(_responding_app, config=config)
    stale_ts = int(time.time()) - 601
    stale = middleware._build_signed_token(stale_ts)
    assert stale is not None

    scope = _make_scope(
        method="GET",
        headers=[_cookie_header({"csrf_token": stale})],
    )
    messages = await _run(middleware, scope)
    pairs = _signed_cookie_pairs(messages)
    assert "set-cookie" in pairs, "stale token must be rotated"
    rotated = pairs["set-cookie"].split("=", 1)[1].split(";", 1)[0]
    assert rotated != stale
    assert middleware._parse_token(rotated) is not None


# ---------------------------------------------------------------------------
# Synchronizer token mode (cache-backed)
# ---------------------------------------------------------------------------


class _FakeCache:
    """In-memory CacheBackendProtocol stand-in for synchronizer-mode tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> Ok:
        return Ok(self.store.get(key))

    async def set(self, key: str, value: str, ttl: int | None = None) -> Ok:
        self.store[key] = value
        return Ok(None)

    async def delete(self, key: str) -> Ok:
        self.store.pop(key, None)
        return Ok(True)


@pytest.mark.asyncio
async def test_synchronizer_get_issues_cache_backed_token() -> None:
    """Safe method in synchronizer mode stores a server-side token."""
    config = CSRFConfig(cookie_name="csrf_token", header_name="X-CSRF-Token")
    cache = _FakeCache()
    middleware = CSRFProtectionMiddleware(_responding_app, config=config, cache=cache)

    scope = _make_scope(method="GET")
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    headers = dict(start.get("headers", []))
    cookie = headers.get(b"set-cookie", b"").decode()
    assert cookie.startswith("csrf_token=")
    ref = cookie.split("=", 1)[1].split(";", 1)[0]
    stored = cache.store.get(f"csrf:sync:{ref}")
    assert stored is not None, "synchronizer token must be stored in cache"
    assert headers.get(b"x-csrf-token", b"").decode() == stored


@pytest.mark.asyncio
async def test_synchronizer_post_matching_token_passes() -> None:
    """POST passing the cache-issued token through the header passes."""
    config = CSRFConfig(cookie_name="csrf_token", header_name="X-CSRF-Token")
    cache = _FakeCache()
    cache.store["csrf:sync:sync-ref-1"] = "server-issued-token"

    inner_called: list[bool] = []
    app = _make_app(called=inner_called)
    middleware = CSRFProtectionMiddleware(app, config=config, cache=cache)

    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": "sync-ref-1"}),
            (b"x-csrf-token", b"server-issued-token"),
        ],
    )
    await _run(middleware, scope)
    assert inner_called


@pytest.mark.asyncio
async def test_synchronizer_post_mismatch_rejected() -> None:
    """POST with a header token differing from the cached one is rejected."""
    config = CSRFConfig(cookie_name="csrf_token", header_name="X-CSRF-Token")
    cache = _FakeCache()
    cache.store["csrf:sync:sync-ref-2"] = "server-issued-token"
    app = _make_app()
    middleware = CSRFProtectionMiddleware(app, config=config, cache=cache)

    scope = _make_scope(
        method="POST",
        headers=[
            _cookie_header({"csrf_token": "sync-ref-2"}),
            (b"x-csrf-token", b"forged-header-token"),
        ],
    )
    messages = await _run(middleware, scope)
    start = next(m for m in messages if m.get("type") == "http.response.start")
    assert start["status"] == 403
