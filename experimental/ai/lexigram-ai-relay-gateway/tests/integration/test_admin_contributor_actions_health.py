"""Action and health-check tests for the relay gateway admin contributor.

Covers the audited mutation action surface (channel state, stream
cancellation) and the structured channel health check payload.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.admin.contributor import RelayGatewayAdminContributor
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.contracts.core.health import HealthStatus

from admin_contributor_support import (
    FakeChecker,
    FakeContainer,
    RecordingAudit,
    StaticPolicyStore,
    _health_service,
    make_services,
)


class TestActions:
    async def _contributor(
        self,
    ) -> tuple[RelayGatewayAdminContributor, StaticPolicyStore, RecordingAudit]:
        audit_log = RecordingAudit()
        controls, _, _, store = make_services(audit=audit_log)
        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(FakeContainer(controls=controls))
        return contributor, store, audit_log

    async def test_set_channel_state_success_is_audited(self) -> None:
        contributor, store, audit = await self._contributor()
        result = await contributor.execute_action(
            "set_channel_state",
            {"channel": "gemini", "enabled": False},
        )
        assert result["ok"] is True
        assert store.current.enabled_channels["gemini"] is False
        assert audit.events, "successful mutation must emit an audit event"

    async def test_set_channel_state_rejects_invalid_params(self) -> None:
        contributor, _, audit = await self._contributor()
        result = await contributor.execute_action(
            "set_channel_state",
            {"enabled": False},
        )
        assert result["ok"] is False
        assert "channel" in result["message"]
        assert not audit.events

    async def test_set_channel_state_rejects_invalid_enabled_flag(self) -> None:
        contributor, _, audit = await self._contributor()
        result = await contributor.execute_action(
            "set_channel_state",
            {"channel": "gemini", "enabled": "banana"},
        )
        assert result["ok"] is False
        assert "boolean" in result["message"]
        assert not audit.events

    async def test_force_cancel_stream_unknown_rejects(self) -> None:
        contributor, _, audit = await self._contributor()
        result = await contributor.execute_action(
            "force_cancel_stream",
            {"stream_id": "does-not-exist"},
        )
        assert result["ok"] is False
        assert not audit.events

    async def test_unknown_action_raises(self) -> None:
        contributor, _, _ = await self._contributor()
        with pytest.raises(LookupError):
            await contributor.execute_action("explode", {})


class TestHealth:
    async def _contributor(
        self, health: RelayHealthService
    ) -> RelayGatewayAdminContributor:
        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(FakeContainer(health=health))
        return contributor

    async def test_render_health_check_returns_health_check_payload(self) -> None:
        """Healthy channels render a structured HEALTHY payload."""
        contributor = await self._contributor(_health_service(FakeChecker()))

        result = await contributor.render_health_check("relay.channels")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.HEALTHY
        assert payload.component == "Relay Channels"
        assert "claude: healthy" in payload.detail
        assert "gemini: healthy" in payload.detail

    async def test_render_health_check_returns_degraded_payload_for_high_latency(
        self,
    ) -> None:
        """A degraded channel renders a structured DEGRADED payload."""
        contributor = await self._contributor(
            _health_service(FakeChecker(ok=True, latency_ms=500.0))
        )

        result = await contributor.render_health_check("relay.channels")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.DEGRADED
        assert payload.component == "Relay Channels"

    async def test_render_health_check_returns_unhealthy_payload_for_failed_probe(
        self,
    ) -> None:
        """A failed channel renders a structured UNHEALTHY payload."""
        contributor = await self._contributor(_health_service(FakeChecker(ok=False)))

        result = await contributor.render_health_check("relay.channels")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.UNHEALTHY
        assert payload.component == "Relay Channels"

    async def test_unknown_health_check_returns_error(self) -> None:
        """Unknown health checks return an error result."""
        contributor = RelayGatewayAdminContributor()
        result = await contributor.render_health_check("unknown")
        assert result.is_err()
