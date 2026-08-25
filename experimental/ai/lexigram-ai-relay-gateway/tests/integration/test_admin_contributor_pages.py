"""Management-page rendering tests for the relay gateway admin contributor.

Covers read-only page degradation without registered dependencies and
full rendering with real gateway services wired in.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.admin.pages import (
    RelayGatewayOverviewPage,
    RelayGatewayRoutesPage,
    RelayGatewaySettingsPage,
    RelayGatewayStreamsPage,
)
from lexigram.ai.relay.gateway.operations.metrics import (
    RelayMetricsService,
    RelayRouteEvent,
)
from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    StatContent,
    TableContent,
)
from lexigram.contracts.ai.relay import RelayFormat

from admin_contributor_support import EmptyRegistry, FakeRequest, make_services


class TestReadOnlyPages:
    async def test_overview_page_renders_without_dependencies(self) -> None:
        page = RelayGatewayOverviewPage()
        content = await page.handle(FakeRequest())
        assert isinstance(content, PageContent)
        assert content.title == "Relay Gateway Overview"
        assert isinstance(content.body, StatContent)
        stats = {s.label: s.value for s in content.body.stats}
        assert stats == {
            "Channels": "N/A",
            "Healthy": "N/A",
            "Active Streams": "N/A",
            "Converter": "N/A",
        }

    async def test_routes_page_renders_without_dependencies(self) -> None:
        page = RelayGatewayRoutesPage()
        content = await page.handle(FakeRequest())
        assert isinstance(content, PageContent)
        assert content.title == "Relay Routes"
        assert isinstance(content.body, EmptyContent)
        assert content.body.message == "Route metrics service is not registered."

    async def test_streams_page_renders_without_dependencies(self) -> None:
        page = RelayGatewayStreamsPage()
        content = await page.handle(FakeRequest())
        assert isinstance(content, PageContent)
        assert content.title == "Relay Streams"
        assert isinstance(content.body, EmptyContent)
        assert content.body.message == "Controls service is not registered."

    async def test_settings_page_renders_without_dependencies(self) -> None:
        page = RelayGatewaySettingsPage()
        content = await page.handle(FakeRequest())
        assert isinstance(content, PageContent)
        assert content.title == "Relay Settings"
        assert isinstance(content.body, EmptyContent)
        assert content.body.message == "Policy store is not registered."


class TestPagesWithDependencies:
    async def test_overview_shows_channel_and_stream_data(self) -> None:
        controls, health, _, _ = make_services()
        page = RelayGatewayOverviewPage(health=health, controls=controls)
        content = await page.handle(FakeRequest())
        assert isinstance(content.body, StatContent)
        stats = {s.label: s.value for s in content.body.stats}
        assert stats["Channels"] == "2"
        assert stats["Healthy"] == "0"
        assert stats["Active Streams"] == "0"
        assert stats["Converter"] == "N/A"
        assert all(stat.icon is not None for stat in content.body.stats)

    async def test_routes_page_renders_route_table(self) -> None:
        _, _, metrics, _ = make_services()
        page = RelayGatewayRoutesPage(metrics=metrics)
        content = await page.handle(FakeRequest())
        assert isinstance(content.body, EmptyContent)
        assert content.body.message == "No route activity in this window."

    async def test_streams_page_renders_active_streams(self) -> None:
        controls, _, _, _ = make_services()
        stream_id, _ = controls.streams.register(
            channel="claude", model="claude-sonnet", request_id="req-1"
        )
        page = RelayGatewayStreamsPage(controls=controls)
        content = await page.handle(FakeRequest())
        assert isinstance(content.body, TableContent)
        assert content.body.columns == (
            "Stream ID",
            "Channel",
            "Model",
            "Request",
            "Started",
        )
        assert any(cell.text == stream_id for row in content.body.rows for cell in row)

    async def test_settings_page_lists_policy_channels(self) -> None:
        _, _, _, store = make_services()
        page = RelayGatewaySettingsPage(policy=store)
        content = await page.handle(FakeRequest())
        assert isinstance(content.body, TableContent)
        first = {row[0].text: row[1].text for row in content.body.rows}
        assert first["claude"] == "enabled"
        assert first["gemini"] == "enabled"
        assert first["Media Schemes"] == "https"
        assert first["Media Hosts"] == "media.example.com"
        assert first["Max Request Bytes"] == "4096"
        assert first["Max Stream Seconds"] == "120"

    async def test_routes_page_paginates_and_builds_base_url(self) -> None:
        from datetime import timedelta

        class EventsWithActivity:
            """Route event source reporting one completed request."""

            async def events(self, window: object) -> tuple[RelayRouteEvent, ...]:
                return (
                    RelayRouteEvent(
                        kind="request_completed",
                        source=RelayFormat.OPENAI_CHAT,
                        target=RelayFormat.CLAUDE,
                        occurred_at=window.start + timedelta(minutes=1),
                    ),
                )

        metrics = RelayMetricsService(
            events=EventsWithActivity(), converter=EmptyRegistry()
        )
        page = RelayGatewayRoutesPage(metrics=metrics)
        content = await page.handle(FakeRequest.with_params(page="1", page_size="2"))
        assert isinstance(content.body, TableContent)
        assert content.body.columns[0] == "Route"
        assert len(content.body.rows) == 1
        assert content.pagination is not None
        assert content.pagination.page == 1
        assert content.pagination.total == 1
        assert content.pagination.per_page == 2
        assert (
            content.pagination.base_url
            == "http://testserver/admin/relay-gateway/overview"
        )
