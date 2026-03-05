"""Relay system integration boot scenarios.

Boots the real relay provider composition (web, http, relay, relay-gateway,
governance, admin) from installed entry points with contract-level fakes
injected through the container, then drives the real ASGI routes.
"""

from __future__ import annotations

import sys

import pytest

from tests.integration.scenarios.relay_fakes import FakeHTTPClient, RelayAppHarness

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


class TestRelayEntryPoints:
    """Entry-point discovery invariants."""

    def test_entry_groups_have_expected_members(
        self, relay_entry_points: dict[str, dict[str, object]]
    ) -> None:
        """Assert every relay entry-point group exposes its contributions."""
        assert "relay-gateway" in relay_entry_points["lexigram.providers"]
        assert "relay" in relay_entry_points["lexigram.providers"]
        assert "relay-gateway" in relay_entry_points["lexigram.ai.modules"]
        assert "relay-gateway" in relay_entry_points["lexigram.web.contributors"]
        assert "relay-gateway" in relay_entry_points["lexigram.admin.contributors"]
        assert "ai-governance" in relay_entry_points["lexigram.admin.contributors"]


class TestRelayBoot:
    """Boot invariants for the composed relay composition."""

    async def test_relay_entry_points_and_boot(
        self, relay_app: RelayAppHarness
    ) -> None:
        """Assert every relay contract resolves exactly once after boot."""
        from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
        from lexigram.contracts.ai.governance import (
            RelayBillingProtocol,
            RelayUsageStoreProtocol,
        )
        from lexigram.contracts.ai.relay import (
            RelayConverterProtocol,
            RelayGatewayProtocol,
        )
        from lexigram.contracts.ai.relay.operations import (
            RelayOperationsControlProtocol,
            RelayOperationsProtocol,
        )
        from lexigram.contracts.events.protocols import EventBusProtocol
        from lexigram.contracts.web import HTTPClientProtocol
        from lexigram.web.contributors import WebContributorRegistry

        harness = relay_app
        container = harness.container

        ops = await container.resolve(RelayOperationsProtocol)
        control = await container.resolve(RelayOperationsControlProtocol)
        billing = await container.resolve(RelayBillingProtocol)
        usage_store = await container.resolve(RelayUsageStoreProtocol)
        events = await container.resolve(EventBusProtocol)
        converter = await container.resolve(RelayConverterProtocol)
        http = await container.resolve(HTTPClientProtocol)
        gateway = await container.resolve(RelayGatewayProtocol)
        admin_registry = await container.resolve(AdminContributorRegistryProtocol)
        web_registry = await container.resolve(WebContributorRegistry)

        fakes = harness.fakes
        assert ops is fakes.operations
        assert control is fakes.operations_control
        assert billing is fakes.billing
        assert usage_store is fakes.usage_store
        assert events is fakes.event_bus
        assert converter is fakes.converter
        assert http is fakes.http_client
        assert gateway is not None
        assert not fakes.billing.reservations

        web_ids = {c.contributor_id for c in web_registry.get_all()}
        assert "relay-gateway" in web_ids
        admin_ids = {c.contributor_id for c in admin_registry.get_all()}
        assert {"relay-gateway", "ai-governance"} <= admin_ids

        # Provider boot must not require any optional LLM SDK import.
        for sdk in ("openai", "anthropic", "google.genai"):
            assert sdk not in sys.modules, f"{sdk} was imported at boot"


class TestRelayBufferedRoute:
    """Buffered chat completions through the booted ASGI app."""

    async def test_chat_completions_round_trip(
        self, relay_app: RelayAppHarness
    ) -> None:
        """POST /v1/chat/completions reaches Claude and echoes the result."""
        from lexigram.contracts.ai.relay import RelayFormat
        from lexigram.testing.clients.web import WebTestClient

        harness = relay_app
        fakes = harness.fakes
        scripted = FakeHTTPClient.with_json(
            200,
            {
                "id": "msg_01",
                "model": "claude-sonnet-4",
                "content": [{"type": "text", "text": "hello from upstream"}],
                "usage": {"input_tokens": 5, "output_tokens": 3},
            },
            headers={"content-type": "application/json"},
        )
        fakes.http_client.responses = scripted.responses
        client = WebTestClient(harness.app)
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "claude-sonnet-4",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 128,
                "stream": False,
            },
            headers={"x-trace-id": "trace-123"},
        )

        assert response.status_code == 200
        body = response.json
        assert body["id"] == "msg_01"
        assert body["content"] == [{"type": "text", "text": "hello from upstream"}]
        assert response.headers["x-request-id"]

        assert len(fakes.http_client.requests) == 1
        method, url, _headers, payload, timeout = fakes.http_client.requests[0]
        assert method == "POST"
        assert url.endswith("/v1/messages")
        assert "relay-upstream.invalid" in url
        assert timeout > 0
        assert payload["model"] == "claude-sonnet-4"
        assert payload["messages"][0]["content"] == [{"type": "text", "text": "ping"}]

        assert (
            "request",
            RelayFormat.OPENAI_CHAT,
            RelayFormat.CLAUDE,
        ) in fakes.converter.conversions
        assert (
            "response",
            RelayFormat.CLAUDE,
            RelayFormat.OPENAI_CHAT,
        ) in fakes.converter.conversions
        assert fakes.authorizer.calls
        assert fakes.billing.reservations
        assert fakes.billing.settlements
