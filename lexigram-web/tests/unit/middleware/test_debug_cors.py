"""Tests for debug-mode permissive CORS auto-detection in WebProvider.

Covers:
- ``WebConfig(server=ServerConfig(debug=True))`` triggers permissive CORS
  (allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]) when no
  explicit CORS origins are configured.
- Explicit CORS ``allow_origins`` config is always respected, even in debug mode.
- Non-debug mode does NOT override CORS to wildcard.
"""

# NOTE: No ``from __future__ import annotations`` — annotation identity
# checks at runtime require real type objects.

from httpx import ASGITransport, AsyncClient
import pytest

from lexigram.web.config import ServerConfig
from lexigram.web.quickstart import _PendingRoute, _QuickstartApp
from lexigram.web.security.config import CORSConfig, CSRFConfig

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_debug_quickstart() -> _QuickstartApp:
    """Return a _QuickstartApp that boots with ``server.debug=True``."""
    qs = _QuickstartApp()

    async def _ensure_booted_debug(self: _QuickstartApp = qs) -> None:
        """Override boot to inject a debug WebConfig."""
        if self._booted:
            return
        from lexigram.app.base import Application
        from lexigram.web.config import WebConfig
        from lexigram.web.di.provider import WebProvider
        from lexigram.identity.di.provider import IdentityProvider
        from lexigram.observability.di.sub_providers.observability import ObservabilityProvider

        web_config = WebConfig(server=ServerConfig(debug=True))
        web_config.security.csrf = CSRFConfig(enabled=False)
        provider = WebProvider(web_config=web_config)
        provider._extra_injectable_services = []
        self._application = Application(name="lexigram-test-debug-cors")
        self._application.add_provider(IdentityProvider())
        self._application.add_provider(ObservabilityProvider())
        self._application._pending_routes = self._collect_script_routes()
        self._application.add_provider(provider)
        await self._application.start()
        self._starlette = provider.starlette
        self._booted = True

    import types

    qs._ensure_booted = types.MethodType(_ensure_booted_debug, qs)  # type: ignore[method-assign]
    return qs


# ---------------------------------------------------------------------------
# Test 1 — server.debug=True enables permissive CORS with default origins
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_debug_mode_enables_permissive_cors() -> None:
    """``server.debug=True`` overrides CORS to wildcard when origins are default.

    Sends a cross-origin request with an ``Origin`` header and asserts that
    the response carries ``access-control-allow-origin: *``.
    """

    async def hello() -> dict:
        return {"ok": True}

    qs = _make_debug_quickstart()
    qs._collect_script_routes = lambda: [  # type: ignore[method-assign]
        _PendingRoute(path="/", method="GET", handler=hello)
    ]

    await qs._ensure_booted()
    async with AsyncClient(
        transport=ASGITransport(app=qs._starlette),
        base_url="http://test",
    ) as client:
        response = await client.get("/", headers={"Origin": "http://example.com"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"


# ---------------------------------------------------------------------------
# Test 2 — explicit CORS origins are respected even in debug mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_cors_config_respected_in_debug_mode() -> None:
    """Explicit ``allow_origins`` is never overridden, even with ``debug=True``.

    When the user explicitly sets CORS origins to a non-default value the
    provider must honour that configuration and NOT substitute wildcard origins.
    """

    async def hello() -> dict:
        return {"ok": True}

    qs = _QuickstartApp()

    async def _boot_explicit(self: _QuickstartApp = qs) -> None:
        if self._booted:
            return
        from lexigram.app.base import Application
        from lexigram.web.config import WebConfig
        from lexigram.web.di.provider import WebProvider
        from lexigram.identity.di.provider import IdentityProvider
        from lexigram.observability.di.sub_providers.observability import ObservabilityProvider

        web_config = WebConfig(
            server=ServerConfig(debug=True),
            cors=CORSConfig(allow_origins=["https://myapp.example.com"]),
        )
        web_config.security.csrf = CSRFConfig(enabled=False)
        provider = WebProvider(web_config=web_config)
        provider._extra_injectable_services = []
        self._application = Application(name="lexigram-test-explicit-cors")
        self._application.add_provider(IdentityProvider())
        self._application.add_provider(ObservabilityProvider())
        self._application._pending_routes = self._collect_script_routes()
        self._application.add_provider(provider)
        await self._application.start()
        self._starlette = provider.starlette
        self._booted = True

    import types

    qs._ensure_booted = types.MethodType(_boot_explicit, qs)  # type: ignore[method-assign]
    qs._collect_script_routes = lambda: [  # type: ignore[method-assign]
        _PendingRoute(path="/", method="GET", handler=hello)
    ]

    await qs._ensure_booted()
    async with AsyncClient(
        transport=ASGITransport(app=qs._starlette),
        base_url="http://test",
    ) as client:
        # Allowed origin
        resp_allowed = await client.get(
            "/", headers={"Origin": "https://myapp.example.com"}
        )
        # Disallowed origin — CORS headers should reflect the specific origin
        resp_other = await client.get("/", headers={"Origin": "http://evil.com"})

    assert resp_allowed.status_code == 200
    # Wildcard should NOT appear when explicit origins are configured
    assert resp_allowed.headers.get("access-control-allow-origin") != "*"
    assert resp_allowed.headers.get("access-control-allow-origin") == (
        "https://myapp.example.com"
    )
    # Disallowed origin gets no CORS origin header
    assert resp_other.headers.get("access-control-allow-origin") is None


# ---------------------------------------------------------------------------
# Test 3 — non-debug mode does NOT set wildcard origins
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_debug_mode_does_not_set_wildcard_cors() -> None:
    """Without ``debug=True``, CORS origins remain as configured (not ``*``).

    Even when the origins are at their default values, a non-debug boot must
    not substitute wildcard origins.
    """

    async def hello() -> dict:
        return {"ok": True}

    qs = _QuickstartApp()

    async def _boot_nodebug(self: _QuickstartApp = qs) -> None:
        if self._booted:
            return
        from lexigram.app.base import Application
        from lexigram.web.config import WebConfig
        from lexigram.web.di.provider import WebProvider
        from lexigram.identity.di.provider import IdentityProvider
        from lexigram.observability.di.sub_providers.observability import ObservabilityProvider

        # Default config — no debug flag, default origins
        web_config = WebConfig()
        web_config.security.csrf = CSRFConfig(enabled=False)
        provider = WebProvider(web_config=web_config)
        provider._extra_injectable_services = []
        self._application = Application(name="lexigram-test-nodebug-cors")
        self._application.add_provider(IdentityProvider())
        self._application.add_provider(ObservabilityProvider())
        self._application._pending_routes = self._collect_script_routes()
        self._application.add_provider(provider)
        await self._application.start()
        self._starlette = provider.starlette
        self._booted = True

    import types

    qs._ensure_booted = types.MethodType(_boot_nodebug, qs)  # type: ignore[method-assign]
    qs._collect_script_routes = lambda: [  # type: ignore[method-assign]
        _PendingRoute(path="/", method="GET", handler=hello)
    ]

    await qs._ensure_booted()
    async with AsyncClient(
        transport=ASGITransport(app=qs._starlette),
        base_url="http://test",
    ) as client:
        # Origin from default allowed list — gets its own header, not wildcard
        response = await client.get("/", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "*"
