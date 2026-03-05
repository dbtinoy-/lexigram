"""Relay gateway failure matrix scenarios.

Boots the booted relay composition from ``conftest.py`` with failing
upstreams and denials, asserting the protocol-error envelopes rendered
by the mounted routes.
"""

from __future__ import annotations

import pytest

from tests.integration.scenarios.relay_fakes import (
    FakeHTTPClient,
    RelayAppHarness,
)

pytestmark = [pytest.mark.integration, pytest.mark.scenario]

RELAY_BODY: dict[str, object] = {
    "model": "claude-sonnet-4",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 32,
}
"""Minimal valid OpenAI chat completions payload for the relay route."""


def _client(harness: RelayAppHarness) -> object:
    """Return a WebTestClient bound to the harness application."""
    from lexigram.testing.clients.web import WebTestClient

    return WebTestClient(harness.app)


class TestRelayFailureMatrix:
    """Client-facing failure classification through the relay routes."""

    async def test_missing_model_is_400(self, relay_app: RelayAppHarness) -> None:
        """A POST without a model must be rejected with a 400 envelope."""
        client = _client(relay_app)
        response = client.post("/v1/chat/completions", json={"messages": []})
        assert response.status_code == 400
        error = response.json["error"]
        assert error["code"] == "INVALID_REQUEST"

    async def test_bad_json_is_400(self, relay_app: RelayAppHarness) -> None:
        """A non-JSON body must be rejected with a 400 envelope."""
        client = _client(relay_app)
        response = client.post(
            "/v1/chat/completions",
            content="{not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400
        assert response.json["error"]["code"] == "INVALID_REQUEST"

    async def test_auth_denial_is_403(self, relay_app: RelayAppHarness) -> None:
        """Authorizer denial must map to a 403 authentication error."""
        relay_app.fakes.authorizer.allowed = False
        client = _client(relay_app)
        response = client.post("/v1/chat/completions", json=RELAY_BODY)
        assert response.status_code == 403
        assert response.json["error"]["code"] == "AUTH_DENIED"

    async def test_quota_denial_is_429(self, relay_app: RelayAppHarness) -> None:
        """Billing quota exhaustion must map to a 429 rate-limit error."""
        relay_app.fakes.billing.fail_message = "monthly quota exhausted"
        client = _client(relay_app)
        response = client.post("/v1/chat/completions", json=RELAY_BODY)
        assert response.status_code == 429
        error = response.json["error"]
        assert error["code"] == "QUOTA_EXCEEDED"
        assert error["message"] == "monthly quota exhausted"

    async def test_unknown_model_is_404(self, relay_app: RelayAppHarness) -> None:
        """An unscheduled model alias must map to a 404 not-found error."""
        client = _client(relay_app)
        response = client.post(
            "/v1/chat/completions",
            json={**RELAY_BODY, "model": "gpt-4o-mini"},
        )
        assert response.status_code == 404
        error = response.json["error"]
        assert error["code"] == "MODEL_NOT_FOUND"
        assert "gpt-4o-mini" in error["message"]

    async def test_malformed_upstream_is_502(self, relay_app: RelayAppHarness) -> None:
        """A 2xx upstream body that is empty must map to a 502 error."""
        relay_app.fakes.http_client.responses = FakeHTTPClient.with_json(
            200, None
        ).responses
        client = _client(relay_app)
        response = client.post("/v1/chat/completions", json=RELAY_BODY)
        assert response.status_code == 502
        error = response.json["error"]
        assert error["code"] == "UPSTREAM_MALFORMED"

    async def test_non_json_upstream_is_502(self, relay_app: RelayAppHarness) -> None:
        """A 2xx upstream body that is not JSON must map to a 502 error."""
        from lexigram.contracts.web import HttpResponse

        relay_app.fakes.http_client.responses = [
            HttpResponse(status=200, body=b"<html>proxy error</html>")
        ]
        client = _client(relay_app)
        response = client.post("/v1/chat/completions", json=RELAY_BODY)
        assert response.status_code == 502
        assert response.json["error"]["code"] == "UPSTREAM_MALFORMED"
