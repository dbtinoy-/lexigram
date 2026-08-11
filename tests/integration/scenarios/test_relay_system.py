"""Relay system integration boot scenarios.

Boots the real relay provider composition (web, http, relay, relay-gateway,
governance, admin) from installed entry points with contract-level fakes
injected through the container, then drives the real ASGI routes.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from lexigram.serialization import dumps_str
from lexigram.serialization import loads as json_loads
from tests.integration.scenarios.relay_fakes import FakeHTTPClient, RelayAppHarness

pytestmark = [pytest.mark.integration, pytest.mark.scenario]

_RELAY_FIXTURES = Path(__file__).parent / "fixtures" / "relay"


def load_relay_fixture(name: str) -> dict[str, object]:
    """Load one stable relay fixture document from the fixtures tree.

    Args:
        name: Fixture file name under ``fixtures/relay``.

    Returns:
        The parsed JSON document.
    """
    document = Path(_RELAY_FIXTURES / name).read_text(encoding="utf-8")
    return json_loads(document)


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

        scenario = load_relay_fixture("openai_chat_to_claude.json")
        request_body = scenario["inbound"]
        assert isinstance(request_body, dict)
        upstream = scenario["upstream"]
        assert isinstance(upstream, dict)
        relay_app.fakes.http_client.responses = FakeHTTPClient.with_json(
            200, upstream
        ).responses
        from lexigram.testing.clients.web import WebTestClient

        harness = relay_app
        fakes = harness.fakes
        client = WebTestClient(harness.app)
        response = client.post(
            "/v1/chat/completions",
            json=request_body,
            headers={"x-trace-id": "trace-123"},
        )

        assert response.status_code == 200
        body = response.json
        assert body["id"] == "msg_01"
        assert body["content"] == [{"type": "text", "text": "pong"}]
        assert response.headers["x-request-id"]

        assert len(fakes.http_client.requests) == 1
        method, url, _headers, payload, timeout = fakes.http_client.requests[0]
        assert method == "POST"
        assert url.endswith("/v1/messages")
        assert "relay-upstream.invalid" in url
        assert timeout > 0
        assert payload["model"] == "claude-sonnet-4"
        assert payload["messages"][0]["content"] == [
            {"type": "text", "text": "You are a helpful assistant."}
        ]
        assert payload["messages"][1]["content"] == [{"type": "text", "text": "ping"}]
        assert payload["temperature"] == 0
        assert payload["max_tokens"] == 128

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


class _ScenarioWireFrame:
    """Minimal scenario wire event exposing ``type`` and ``to_dict``."""

    def __init__(self, type_: str) -> None:
        self.type = type_

    def to_dict(self) -> dict[str, object]:
        """The wire payload is the discriminant alone."""
        return {"type": self.type}


class _ScenarioStreamSession:
    """Stream session echoing source events as labeled wire frames.

    A scenario-local session because the bundle's ``FakeStreamSession``
    echoes arbitrary payloads without ``to_dict``; this one always emits
    DTO-shaped wire events the SSE encoder can frame.
    """

    def __init__(self) -> None:
        """Create an empty, unfinalized session."""
        self.accepted: list[str] = []
        self.finalized = False

    def accept(self, event: object) -> tuple[_ScenarioWireFrame, ...]:
        """Record the source DTO and re-emit it as a labeled frame."""
        label = str(getattr(event, "type", "event"))
        self.accepted.append(label)
        return (_ScenarioWireFrame(label),)

    def finalize(self) -> tuple[_ScenarioWireFrame, ...]:
        """Emit one terminal frame exactly once."""
        if self.finalized:
            return ()
        self.finalized = True
        return (_ScenarioWireFrame("message_stop"),)

    def snapshot(self) -> dict[str, object]:
        """Return the session bookkeeping snapshot."""
        return {"accepted": len(self.accepted), "finalized": self.finalized}


class TestRelayStreamingRoute:
    """Streaming chat completions through the booted ASGI app."""

    async def test_chat_completions_stream_round_trip(
        self, relay_app: RelayAppHarness
    ) -> None:
        """POST /v1/chat/completions with stream flows SSE frames and settles."""
        from lexigram.contracts.web import HttpResponse

        scenario = load_relay_fixture("claude_stream_to_openai.json")
        events = scenario["upstream_events"]
        assert isinstance(events, list)

        body = "".join(
            "data: " + dumps_str(event) + "\n\n"
            for event in events
            if isinstance(event, dict)
        )
        harness = relay_app
        fakes = harness.fakes
        fakes.http_client.responses = [
            HttpResponse(status=200, headers={}, body=body.encode("utf-8"))
        ]
        fakes.converter.session = _ScenarioStreamSession()

        from lexigram.testing.clients.web import WebTestClient

        client = WebTestClient(harness.app)
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "claude-sonnet-4",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 128,
                "stream": True,
            },
            headers={"x-trace-id": "trace-456"},
        )

        assert response.status_code == 200, response.text
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert response.headers["x-request-id"]

        text = response.text
        frames = [
            line[6:].strip() for line in text.splitlines() if line.startswith("data: ")
        ]
        assert frames, "SSE body carried no data frames"
        assert frames[-1] == "[DONE]"
        parsed = [json_loads(frame) for frame in frames[:-1]]
        assert all(isinstance(item, dict) and "type" in item for item in parsed)
        parsed_types = {item["type"] for item in parsed}
        assert {"message_start", "content_block_delta", "message_stop"} <= parsed_types
        assert len(frames) - 1 >= len(events)

        assert len(fakes.http_client.requests) == 1
        method, url, _headers, payload, timeout = fakes.http_client.requests[0]
        assert method == "POST"
        assert url.endswith("/v1/messages")
        assert isinstance(payload, dict)
        assert timeout > 0

        assert fakes.authorizer.calls
        assert fakes.billing.reservations
        assert [status for _rid, status, _cid, _usage in fakes.billing.settlements] == [
            "completed"
        ]


class TestRelayAdminContributor:
    """Admin contributor discovery, rendering, and permissioned controls."""

    async def test_contributor_discovery_matches_expectations(
        self, relay_app: RelayAppHarness
    ) -> None:
        """Every declared artifact on both AI contributors is registered."""
        from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol

        expectations = load_relay_fixture("admin_expectations.json")
        expected = expectations["contributors"]
        assert isinstance(expected, dict)

        container = relay_app.container
        registry = await container.resolve(AdminContributorRegistryProtocol)
        by_id = {c.contributor_id: c for c in registry.get_all()}
        for contributor_id in expected:
            assert (
                sum(1 for c in registry.get_all() if c.contributor_id == contributor_id)
                == 1
            ), f"{contributor_id} registered more than once"

        for contributor_id, spec in expected.items():
            contributor = by_id[contributor_id]
            assert isinstance(spec, dict)
            assert contributor.display_name == spec["display_name"]
            assert contributor.group == spec["group"]
            assert contributor.priority == spec["priority"]
            assert set(contributor.required_permissions) == set(
                spec["required_permissions"]
            )
            assert [w.name for w in contributor.get_dashboard_widgets()] == spec[
                "widgets"
            ]
            assert [h.name for h in contributor.get_health_definitions()] == spec[
                "health_checks"
            ]
            assert [a.name for a in contributor.get_actions()] == spec["actions"]
            assert [p.name for p in contributor.get_management_pages()] == spec["pages"]

    async def test_channel_health_widget_renders(
        self, relay_app: RelayAppHarness
    ) -> None:
        """The channel health widget renders a health-snapshot report."""
        from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
        from lexigram.contracts.admin.types import WidgetParams

        container = relay_app.container
        registry = await container.resolve(AdminContributorRegistryProtocol)
        contributor = registry.get("relay-gateway")
        result = await contributor.render_widget(
            "channel_health", WidgetParams(page=1, page_size=5)
        )
        assert result.is_ok()
        content = result.unwrap().content
        assert "claude" in repr(content)
        assert "channel" in repr(content).lower()

    async def test_permitted_operator_can_drain_channel(
        self, relay_app: RelayAppHarness
    ) -> None:
        """A permitted operator action updates policy and records audit."""
        expectations = load_relay_fixture("admin_expectations.json")
        control = expectations["control"]
        assert isinstance(control, dict)
        channel = control["channel"]
        assert isinstance(channel, str)
        actor_id = control["operator_actor_id"]
        assert isinstance(actor_id, str)

        from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol

        container = relay_app.container
        registry = await container.resolve(AdminContributorRegistryProtocol)
        contributor = registry.get("relay-gateway")

        relay_app.fakes.authorizer.allowed = True
        result = await contributor.execute_action(
            "set_channel_state",
            {"channel": channel, "enabled": False, "actor_id": actor_id},
        )
        assert result.get("ok") is True, result

        from lexigram.contracts.ai.relay.operations import RelayPolicyStoreProtocol

        policy_store = await container.resolve(RelayPolicyStoreProtocol)
        snapshot = await policy_store.load()
        assert snapshot.enabled_channels[channel] is False

        audit_events = relay_app.fakes.audit_store.events
        assert audit_events
        event = audit_events[-1]
        assert event.user_id == actor_id
        assert event.metadata["action"] == "relay.channel_control"
        assert event.metadata["new"] == {"enabled": False}

    async def test_unpermitted_operator_is_rejected(
        self, relay_app: RelayAppHarness
    ) -> None:
        """A denied operator cannot mutate the policy snapshot."""
        expectations = load_relay_fixture("admin_expectations.json")
        control = expectations["control"]
        assert isinstance(control, dict)
        channel = control["channel"]
        assert isinstance(channel, str)
        denied_actor = control["denied_actor_id"]
        assert isinstance(denied_actor, str)

        from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol

        container = relay_app.container
        registry = await container.resolve(AdminContributorRegistryProtocol)
        contributor = registry.get("relay-gateway")

        from lexigram.contracts.ai.relay.operations import RelayPolicyStoreProtocol

        policy_store = await container.resolve(RelayPolicyStoreProtocol)
        before = await policy_store.load()

        relay_app.fakes.authorizer.allowed = False
        result = await contributor.execute_action(
            "set_channel_state",
            {"channel": channel, "enabled": False, "actor_id": denied_actor},
        )
        assert result.get("ok") is False

        after = await policy_store.load()
        assert after.enabled_channels[channel] == before.enabled_channels[channel]

        audit_events = relay_app.fakes.audit_store.events
        assert not any(e.user_id == denied_actor for e in audit_events)
