"""Tests for the fixed-window rate limiter and in-memory counter."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.ratelimit import (
    InMemoryRateLimitCounter,
    RelayRateLimiter,
)
from lexigram.ai.relay.gateway.web.routes import _with_auth_guard
from lexigram.contracts.ai.relay import (
    RelayAuthIdentity,
    RelayAuthVerifierProtocol,
    RelayRateLimitCounterProtocol,
    RelayRateLimitDecision,
)
from lexigram.contracts.core.result import Ok
from lexigram.serialization import loads


async def test_window_expiry_resets_counter() -> None:
    counter = InMemoryRateLimitCounter()
    first = await counter.take("k", limit=2, window_seconds=60)
    assert first.allowed is True
    assert first.count == 1
    second = await counter.take("k", limit=2, window_seconds=60)
    assert second.count == 2
    assert second.allowed is True
    third = await counter.take("k", limit=2, window_seconds=60)
    assert third.allowed is False
    assert third.count == 3


async def test_limit_enforcement_rejects_over_limit() -> None:
    counter = InMemoryRateLimitCounter()
    for _ in range(30):
        decision = await counter.take("k", limit=30, window_seconds=300)
        assert decision.allowed is True
    denied = await counter.take("k", limit=30, window_seconds=300)
    assert denied.allowed is False
    assert denied.count == 31


async def test_key_isolation() -> None:
    counter = InMemoryRateLimitCounter()
    await counter.take("a", limit=1, window_seconds=60)
    result = await counter.take("b", limit=1, window_seconds=60)
    assert result.allowed is True
    assert result.count == 1


async def test_ttl_counts_down_within_window() -> None:
    counter = InMemoryRateLimitCounter()
    first = await counter.take("k", limit=1, window_seconds=10)
    assert first.ttl_seconds > 0
    assert first.ttl_seconds <= 10


async def test_limiter_no_rules_returns_none() -> None:
    limiter = RelayRateLimiter(rules={}, counter=InMemoryRateLimitCounter())
    identity = RelayAuthIdentity(user_id="u1", token_id="t1")
    assert await limiter.check(identity, model="gpt-4") is None


async def test_limiter_no_counter_returns_none() -> None:
    limiter = RelayRateLimiter(rules={"*": {"max": 1, "window_seconds": 60}})
    identity = RelayAuthIdentity(user_id="u1", token_id="t1")
    assert await limiter.check(identity, model="gpt-4") is None


async def test_limiter_token_wide_rule() -> None:
    counter = InMemoryRateLimitCounter()
    limiter = RelayRateLimiter(
        rules={"*": {"max": 1, "window_seconds": 60}}, counter=counter
    )
    identity = RelayAuthIdentity(user_id="u1", token_id="t1")
    first = await limiter.check(identity, model="gpt-4")
    assert first is not None
    assert first.allowed is True
    second = await limiter.check(identity, model="gpt-4")
    assert second is not None
    assert second.allowed is False


async def test_limiter_model_rule_takes_precedence() -> None:
    counter = InMemoryRateLimitCounter()
    limiter = RelayRateLimiter(
        rules={
            "*": {"max": 10, "window_seconds": 60},
            "gpt-4": {"max": 1, "window_seconds": 60},
        },
        counter=counter,
    )
    identity = RelayAuthIdentity(user_id="u1", token_id="t1")
    first = await limiter.check(identity, model="gpt-4")
    assert first is not None
    assert first.allowed is True
    second = await limiter.check(identity, model="gpt-4")
    assert second.allowed is False
    other = await limiter.check(identity, model="claude-3")
    assert other is not None
    assert other.allowed is True


async def test_limiter_keys_are_per_token() -> None:
    counter = InMemoryRateLimitCounter()
    limiter = RelayRateLimiter(
        rules={"gpt-4": {"max": 1, "window_seconds": 60}}, counter=counter
    )
    identity_a = RelayAuthIdentity(user_id="u1", token_id="t1")
    identity_b = RelayAuthIdentity(user_id="u2", token_id="t2")
    await limiter.check(identity_a, model="gpt-4")
    result = await limiter.check(identity_b, model="gpt-4")
    assert result is not None
    assert result.allowed is True


async def test_protocol_compliance() -> None:
    assert isinstance(InMemoryRateLimitCounter(), RelayRateLimitCounterProtocol)
    decision = RelayRateLimitDecision(allowed=True, count=1, ttl_seconds=10)
    assert decision.allowed is True


# --- route-level guard composition ---


class FakeVerifier:
    """Minimal ``RelayAuthVerifierProtocol`` double with a canned identity."""

    async def authenticate(self, request: object) -> object:
        return Ok(RelayAuthIdentity(user_id="u1", token_id="t1"))


class FakeRateLimitContainer:
    """Container double resolving config, verifier, and counter bindings."""

    def __init__(
        self,
        config: object,
        verifier: FakeVerifier | None = None,
        counter: RelayRateLimitCounterProtocol | None = None,
    ) -> None:
        self._config = config
        self._verifier = verifier
        self._counter = counter

    async def resolve_optional(self, service_type: type[Any]) -> Any | None:
        if service_type is RelayGatewayConfig:
            return self._config
        if service_type is RelayAuthVerifierProtocol:
            return self._verifier
        if service_type is RelayRateLimitCounterProtocol:
            return self._counter
        return None


def _make_request(body: bytes = b'{"model": "gpt-4"}') -> Request:
    """Build a request that streams *body* exactly once, cached by Starlette."""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
        },
        receive=receive,
    )


async def _echo_handler(request: Request) -> JSONResponse:
    """Trivial endpoint double."""
    return JSONResponse({"ok": True})


async def test_guarded_route_second_request_gets_429() -> None:
    container = FakeRateLimitContainer(
        config=RelayGatewayConfig(
            require_auth=True,
            rate_limits={"*": {"max": 1, "window_seconds": 60}},
        ),
        verifier=FakeVerifier(),
        counter=InMemoryRateLimitCounter(),
    )
    guarded = _with_auth_guard(_echo_handler)
    first = _make_request()
    first.state.container = container
    response = await guarded(first)
    assert response.status_code == 200
    second = _make_request()
    second.state.container = container
    response = await guarded(second)
    assert response.status_code == 429
    envelope = loads(response.body)
    assert envelope["error"]["type"] == "rate_limit_error"
    assert envelope["error"]["code"] == "RATE_LIMITED"
    assert isinstance(envelope["error"]["retry_after_seconds"], int)


async def test_guarded_route_succeeds_without_rules() -> None:
    container = FakeRateLimitContainer(
        config=RelayGatewayConfig(require_auth=True),
        verifier=FakeVerifier(),
        counter=InMemoryRateLimitCounter(),
    )
    guarded = _with_auth_guard(_echo_handler)
    for _ in range(2):
        request = _make_request()
        request.state.container = container
        response = await guarded(request)
        assert response.status_code == 200


async def test_guarded_route_succeeds_without_container() -> None:
    guarded = _with_auth_guard(_echo_handler)
    for _ in range(2):
        response = await guarded(_make_request())
        assert response.status_code == 200
