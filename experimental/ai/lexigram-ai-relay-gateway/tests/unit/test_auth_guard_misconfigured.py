"""Route-level auth-guard matrix: off / bound / required-but-unbound.

Exercises ``_with_auth_guard`` for the three verifier states with a
container double, confirming auth-off passes through (200), a bound
verifier authenticates (200 / 401), and required-but-unbound fails
closed with a 503.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.web.routes import _with_auth_guard
from lexigram.contracts.ai.relay import (
    RelayAuthError,
    RelayAuthIdentity,
    RelayAuthVerifierProtocol,
)
from lexigram.contracts.core.result import Err, Ok, Result


class FakeVerifier:
    """Minimal verifier double authenticating every request."""

    async def authenticate(
        self, request: object
    ) -> Result[RelayAuthIdentity, RelayAuthError]:
        return Ok(RelayAuthIdentity(user_id="u1", token_id="t1"))


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
        if service_type is RelayGatewayConfig:
            return self._config
        if service_type is RelayAuthVerifierProtocol:
            return self._verifier
        return None


class FakeRejectingVerifier:
    """Verifier double rejecting every request with a 401 error."""

    async def authenticate(
        self, request: object
    ) -> Result[RelayAuthIdentity, RelayAuthError]:
        return Err(RelayAuthError("AUTH_TOKEN_INVALID", "invalid token"))


def _make_request(container: object) -> Request:
    """Build a minimal inbound request carrying the container double."""

    req = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
        }
    )
    req.state.container = container
    return req


async def _ok_handler(request: Request) -> JSONResponse:
    """Trivial success handler proving the wrapped route runs."""
    return JSONResponse({"ok": True})


async def test_auth_off_passes_through() -> None:
    """No container / no config keeps the route open (auth explicitly off)."""
    route = _with_auth_guard(_ok_handler)
    response = await route(_make_request(None))
    assert response.status_code == 200


async def test_auth_off_when_require_auth_false() -> None:
    container = FakeContainer(config=RelayGatewayConfig(require_auth=False))
    response = await _with_auth_guard(_ok_handler)(
        _make_request(container)
    )
    assert response.status_code == 200


async def test_bound_verifier_authenticates() -> None:
    container = FakeContainer(
        config=RelayGatewayConfig(require_auth=True),
        verifier=FakeVerifier(),
    )
    response = await _with_auth_guard(_ok_handler)(
        _make_request(container)
    )
    assert response.status_code == 200


async def test_bound_verifier_rejects_invalid_credentials() -> None:
    container = FakeContainer(
        config=RelayGatewayConfig(require_auth=True),
        verifier=FakeRejectingVerifier(),
    )
    response = await _with_auth_guard(_ok_handler)(
        _make_request(container)
    )
    assert response.status_code == 401
    assert "AUTH_TOKEN_INVALID" in response.body.decode()


async def test_required_but_unbound_fails_closed() -> None:
    container = FakeContainer(config=RelayGatewayConfig(require_auth=True))
    response = await _with_auth_guard(_ok_handler)(
        _make_request(container)
    )
    assert response.status_code == 503
    assert "AUTH_REQUIRED_BUT_UNBOUND" in response.body.decode()