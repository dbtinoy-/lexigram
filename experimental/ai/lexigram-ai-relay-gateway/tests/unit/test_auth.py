"""Tests for the gateway auth guard (protocol slot, fake verifier)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.web.routes import _resolve_verifier
from lexigram.ai.relay.gateway.web.shared import (
_REQUIRE_AUTH_MISCONFIGURED,
    auth_guard,
)
from lexigram.contracts.ai.relay import (
    RelayAuthError,
    RelayAuthIdentity,
    RelayAuthVerifierProtocol,
)
from lexigram.contracts.core.result import Err, Ok, Result


class FakeVerifier:
    """Minimal ``RelayAuthVerifierProtocol`` double with a canned outcome."""

    def __init__(self, ok: bool = True) -> None:
        self.ok = ok

    async def authenticate(
        self, request: object
    ) -> Result[RelayAuthIdentity, RelayAuthError]:
        """Return the canned identity or rejection."""
        if self.ok:
            return Ok(RelayAuthIdentity(user_id="u1", token_id="t1"))
        return Err(RelayAuthError("AUTH_TOKEN_INVALID", "invalid token"))


class FakeContainer:
    """Container double resolving the config and verifier bindings."""

    def __init__(
        self,
        config: RelayGatewayConfig | None = None,
        verifier: FakeVerifier | None = None,
    ) -> None:
        self._config = config
        self._verifier = verifier

    async def resolve_optional(self, service_type: type[Any]) -> Any | None:
        """Resolve the config or verifier binding, else ``None``."""
        if service_type is RelayGatewayConfig:
            return self._config
        if service_type is RelayAuthVerifierProtocol:
            return self._verifier
        return None


async def handler(request: Request) -> JSONResponse:
    """Echo a trivial success response."""
    return JSONResponse({"ok": True})


def _make_request() -> Request:
    """Build a minimal inbound request with an empty state."""
    return Request(
        {"type": "http", "method": "POST", "path": "/v1/chat/completions", "headers": []}
    )


async def test_auth_guard_rejects_when_verifier_fails() -> None:
    response = await auth_guard(_make_request(), FakeVerifier(ok=False), handler)
    assert response.status_code == 401
    assert "AUTH_TOKEN_INVALID" in response.body.decode()


async def test_auth_guard_passes_when_verifier_ok() -> None:
    request = _make_request()
    response = await auth_guard(request, FakeVerifier(ok=True), handler)
    assert response.status_code == 200
    assert request.state.relay_identity == RelayAuthIdentity(user_id="u1", token_id="t1")


async def test_auth_guard_allows_when_no_verifier() -> None:
    response = await auth_guard(_make_request(), None, handler)
    assert response.status_code == 200


async def test_auth_guard_fails_closed_when_required_but_unbound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lexigram.ai.relay.gateway.web import shared

    error_log = MagicMock()
    fake_logger = MagicMock()
    fake_logger.error = error_log
    monkeypatch.setattr(shared, "logger", fake_logger)
    response = await auth_guard(_make_request(), _REQUIRE_AUTH_MISCONFIGURED, handler)
    assert response.status_code == 503
    assert "AUTH_REQUIRED_BUT_UNBOUND" in response.body.decode()
    error_log.assert_called_once_with("relay_auth_required_but_unbound")


async def test_resolve_verifier_fails_closed_without_container() -> None:
    """No container at all means we cannot prove the auth opt-out —
    require_auth defaults to True, so fail closed (503 sentinel)."""
    assert await _resolve_verifier(_make_request()) is _REQUIRE_AUTH_MISCONFIGURED


async def test_resolve_verifier_fails_closed_when_config_unbound() -> None:
    """A container without RelayGatewayConfig is misconfiguration, not an
    explicit opt-out — fail closed."""
    request = _make_request()
    request.state.container = FakeContainer(config=None)
    assert await _resolve_verifier(request) is _REQUIRE_AUTH_MISCONFIGURED


async def test_resolve_verifier_is_none_when_auth_not_required() -> None:
    request = _make_request()
    request.state.container = FakeContainer(
        config=RelayGatewayConfig(require_auth=False)
    )
    assert await _resolve_verifier(request) is None


async def test_resolve_verifier_is_misconfigured_sentinel_when_verifier_unbound() -> None:
    request = _make_request()
    request.state.container = FakeContainer(
        config=RelayGatewayConfig(require_auth=True), verifier=None
    )
    assert await _resolve_verifier(request) is _REQUIRE_AUTH_MISCONFIGURED


async def test_resolve_verifier_returns_bound_verifier() -> None:
    request = _make_request()
    request.state.container = FakeContainer(
        config=RelayGatewayConfig(require_auth=True), verifier=FakeVerifier(ok=True)
    )
    verifier = await _resolve_verifier(request)
    assert verifier is not None
    assert isinstance(verifier, FakeVerifier)


async def test_resolve_verifier_uses_fallback_container() -> None:
    """Mount-time container fallback mirrors the contributor resolvers:
    without request.state.container, the guard still resolves auth."""
    fallback = FakeContainer(
        config=RelayGatewayConfig(require_auth=True), verifier=FakeVerifier(ok=True)
    )
    verifier = await _resolve_verifier(_make_request(), fallback_container=fallback)
    assert verifier is not None
    assert isinstance(verifier, FakeVerifier)


async def test_resolve_verifier_fallback_honors_opt_out() -> None:
    fallback = FakeContainer(config=RelayGatewayConfig(require_auth=False))
    assert await _resolve_verifier(_make_request(), fallback_container=fallback) is None
