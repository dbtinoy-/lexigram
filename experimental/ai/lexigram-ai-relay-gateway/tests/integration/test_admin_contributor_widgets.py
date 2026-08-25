"""Dashboard-widget tests for the relay gateway admin contributor.

Covers widget rendering with real services wired in, unknown-widget
errors, and the unavailable-state fallback when dependencies are
missing.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.admin.contributor import RelayGatewayAdminContributor
from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService
from lexigram.contracts.admin.widget_content import MessageContent, TableContent

from admin_contributor_support import FakeContainer, WIDGET_PARAMS, make_services


class TestWidgets:
    async def _contributor(
        self,
        *,
        controls: RelayControlsService | None = None,
        health: RelayHealthService | None = None,
        metrics: RelayMetricsService | None = None,
    ) -> RelayGatewayAdminContributor:
        contributor = RelayGatewayAdminContributor()
        await contributor.on_admin_boot(
            FakeContainer(controls=controls, health=health, metrics=metrics)
        )
        return contributor

    async def test_channel_health_widget_renders_status(self) -> None:
        _, health, _, _ = make_services()
        contributor = await self._contributor(health=health)
        result = await contributor.render_widget("channel_health", WIDGET_PARAMS)
        assert result.is_ok()
        content = result.unwrap().content
        assert isinstance(content, TableContent)
        assert content.columns[0] == "Channel"
        assert any(cell.text == "claude" for row in content.rows for cell in row)

    async def test_route_activity_widget_renders_empty_state(self) -> None:
        _, _, metrics, _ = make_services()
        contributor = await self._contributor(metrics=metrics)
        result = await contributor.render_widget("route_activity", WIDGET_PARAMS)
        assert result.is_ok()
        content = result.unwrap().content
        assert isinstance(content, TableContent)
        assert content.rows == ()
        assert content.empty_message == "No route activity in this window."

    async def test_active_streams_widget_renders_stream(self) -> None:
        controls, _, _, _ = make_services()
        controls.streams.register(
            channel="claude", model="claude-sonnet", request_id="req-x"
        )
        contributor = await self._contributor(controls=controls)
        result = await contributor.render_widget("active_streams", WIDGET_PARAMS)
        assert result.is_ok()
        content = result.unwrap().content
        assert isinstance(content, TableContent)
        assert any(cell.text == "claude" for row in content.rows for cell in row)

    async def test_unknown_widget_returns_error(self) -> None:
        contributor = await self._contributor()
        result = await contributor.render_widget("unknown", WIDGET_PARAMS)
        assert result.is_err()

    async def test_widgets_without_dependencies_render_unavailable(self) -> None:
        contributor = await self._contributor()
        for widget in ("channel_health", "route_activity", "active_streams"):
            result = await contributor.render_widget(widget, WIDGET_PARAMS)
            assert result.is_ok(), widget
            content = result.unwrap().content
            assert isinstance(content, MessageContent), widget
            assert "unavailable" in content.text.lower(), widget
