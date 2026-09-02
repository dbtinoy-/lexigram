"""Tests for lexigram-events admin contributor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.admin import MessageContent, StatContent
from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.contracts.admin.widget_protocols import WidgetHandlerProtocol
from lexigram.events.admin.contributor import EventsAdminContributor
from lexigram.events.admin.handlers.dead_letter_count import (
    DeadLetterCountWidgetHandler,
)
from lexigram.events.admin.handlers.events_throughput import (
    EventsThroughputWidgetHandler,
)
from lexigram.result import Ok


class TestEventsAdminContributor:
    """Tests for EventsAdminContributor."""

    @pytest.fixture
    def mock_throughput_handler(self) -> MagicMock:
        """Mock EventsThroughputWidgetHandler returning MessageContent."""
        handler = MagicMock(spec=WidgetHandlerProtocol)
        handler.get_data = AsyncMock(
            return_value=Ok(
                MessageContent(text="stub", tone="default")
            )
        )
        return handler

    @pytest.fixture
    def mock_dead_letter_handler(self) -> MagicMock:
        """Mock DeadLetterCountWidgetHandler returning StatContent."""
        handler = MagicMock(spec=WidgetHandlerProtocol)
        handler.get_data = AsyncMock(return_value=Ok(StatContent(stats=())))
        return handler

    @pytest.fixture
    def mock_container(
        self,
        mock_throughput_handler: MagicMock,
        mock_dead_letter_handler: MagicMock,
    ) -> MagicMock:
        """Mock container that resolves handlers."""
        container = MagicMock()
        handler_map = {
            EventsThroughputWidgetHandler: mock_throughput_handler,
            DeadLetterCountWidgetHandler: mock_dead_letter_handler,
        }
        container.resolve = AsyncMock(side_effect=handler_map.get)
        return container

    @pytest.fixture
    def contributor(
        self,
        mock_container: MagicMock,
    ) -> EventsAdminContributor:
        """Create contributor booted with the mocked handlers via container."""
        return EventsAdminContributor()

    @pytest.fixture
    async def booted_contributor(
        self,
        contributor: EventsAdminContributor,
        mock_container: MagicMock,
    ) -> EventsAdminContributor:
        """Boot the contributor through the mocked container."""
        await contributor.on_admin_boot(mock_container)
        return contributor

    @pytest.mark.asyncio
    async def test_render_widget_throughput(
        self,
        booted_contributor: EventsAdminContributor,
        mock_throughput_handler: MagicMock,
    ) -> None:
        """Render events_throughput widget passes MessageContent through."""
        result = await booted_contributor.render_widget(
            "events_throughput", WidgetParams()
        )
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, MessageContent)
        mock_throughput_handler.get_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_render_widget_dead_letter(
        self,
        booted_contributor: EventsAdminContributor,
        mock_dead_letter_handler: MagicMock,
    ) -> None:
        """Render dead_letter_count widget passes StatContent through."""
        result = await booted_contributor.render_widget(
            "dead_letter_count", WidgetParams()
        )
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        mock_dead_letter_handler.get_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_render_unknown_widget(
        self, booted_contributor: EventsAdminContributor
    ) -> None:
        """Unknown widget name returns WidgetNotFoundError."""
        result = await booted_contributor.render_widget("nonexistent", WidgetParams())
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)
        assert error.contributor_name == "events"
        assert error.widget_name == "nonexistent"

    def test_get_dashboard_widgets(self, contributor: EventsAdminContributor) -> None:
        """Contributor returns three dashboard widgets."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 3
        names = {w.name for w in widgets}
        assert names == {"events_throughput", "dead_letter_count", "live_events"}

    def test_get_navigation_items(self, contributor: EventsAdminContributor) -> None:
        """Contributor returns navigation items."""
        items = contributor.get_navigation_items()
        assert len(items) > 0
        root = next((i for i in items if i.label == "Events"), None)
        assert root is not None

    def test_get_health_definitions(self, contributor: EventsAdminContributor) -> None:
        """Contributor returns health definitions."""
        defs = contributor.get_health_definitions()
        assert len(defs) > 0


__all__ = [
    "TestEventsAdminContributor",
]

class TestWidgetAdvertising:
    """Post-boot widget filtering (R49 — docs/09-01-2026/45-dead-dashboard-widgets.md).

    Before boot the full declarative catalog is advertised (covered by
    ``test_get_dashboard_widgets`` above); after boot only widgets whose
    handler resolved are shown, so deployments without the events wiring
    never render permanently dead dashboard shells.
    """

    @pytest.mark.asyncio
    async def test_booted_contributor_advertises_only_resolved(self) -> None:
        throughput = MagicMock(spec=WidgetHandlerProtocol)
        container = MagicMock()
        container.resolve = AsyncMock(
            side_effect={EventsThroughputWidgetHandler: throughput}.get
        )
        contributor = EventsAdminContributor()
        await contributor.on_admin_boot(container)

        names = {w.name for w in contributor.get_dashboard_widgets()}
        assert names == {"events_throughput"}

    @pytest.mark.asyncio
    async def test_boot_without_container_advertises_nothing(self) -> None:
        contributor = EventsAdminContributor()
        await contributor.on_admin_boot(None)
        assert list(contributor.get_dashboard_widgets()) == []

    @pytest.mark.asyncio
    async def test_boot_with_failing_container_advertises_nothing(self) -> None:
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=RuntimeError("not registered"))
        contributor = EventsAdminContributor()
        await contributor.on_admin_boot(container)
        assert list(contributor.get_dashboard_widgets()) == []

    @pytest.mark.asyncio
    async def test_render_widget_still_errs_for_unresolved(self) -> None:
        """Direct endpoint hits keep the structured error (friendly card)."""
        contributor = EventsAdminContributor()
        await contributor.on_admin_boot(None)
        result = await contributor.render_widget("live_events", WidgetParams())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)
