"""Tests for lexigram-events admin contributor and handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

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
from lexigram.events.admin.renderer import PackageWidgetRenderer
from lexigram.events.admin.viewmodels import (
    DeadLetterCountViewModel,
    EventsThroughputViewModel,
)
from lexigram.result import Ok


class TestEventsThroughputWidgetHandler:
    """Tests for EventsThroughputWidgetHandler."""

    @pytest.fixture
    def mock_event_bus(self) -> MagicMock:
        """Mock EventBusProtocol."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_event_bus: MagicMock) -> EventsThroughputWidgetHandler:
        """Create handler with mocked event bus."""
        return EventsThroughputWidgetHandler(event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_get_data_returns_viewmodel(
        self, handler: EventsThroughputWidgetHandler
    ) -> None:
        """Handler returns EventsThroughputViewModel."""
        result = await handler.get_data(WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, EventsThroughputViewModel)
        assert vm.window_minutes == 60

    @pytest.mark.asyncio
    async def test_get_data_respects_time_window(
        self, handler: EventsThroughputWidgetHandler
    ) -> None:
        """Handler uses time_window_minutes from params."""
        params = WidgetParams(time_window_minutes=30)
        result = await handler.get_data(params)
        assert result.is_ok()
        vm = result.unwrap()
        assert vm.window_minutes == 30


class TestDeadLetterCountWidgetHandler:
    """Tests for DeadLetterCountWidgetHandler."""

    @pytest.fixture
    def mock_event_bus(self) -> MagicMock:
        """Mock EventBusProtocol."""
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_event_bus: MagicMock) -> DeadLetterCountWidgetHandler:
        """Create handler with mocked event bus."""
        return DeadLetterCountWidgetHandler(event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_get_data_returns_viewmodel(
        self, handler: DeadLetterCountWidgetHandler
    ) -> None:
        """Handler returns DeadLetterCountViewModel."""
        result = await handler.get_data(WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, DeadLetterCountViewModel)
        assert vm.count == 0


class TestEventsAdminContributor:
    """Tests for EventsAdminContributor."""

    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        """Mock PackageWidgetRenderer."""
        renderer = MagicMock(spec=PackageWidgetRenderer)
        renderer.render = MagicMock(return_value="<div>widget</div>")
        return renderer

    @pytest.fixture
    def mock_throughput_handler(self) -> MagicMock:
        """Mock EventsThroughputWidgetHandler."""
        handler = MagicMock(spec=WidgetHandlerProtocol)
        handler.get_data = AsyncMock(
            return_value=Ok(
                EventsThroughputViewModel(
                    events_per_second=5.0, total_events=300, window_minutes=60
                )
            )
        )
        return handler

    @pytest.fixture
    def mock_dead_letter_handler(self) -> MagicMock:
        """Mock DeadLetterCountWidgetHandler."""
        handler = MagicMock(spec=WidgetHandlerProtocol)
        handler.get_data = AsyncMock(
            return_value=Ok(DeadLetterCountViewModel(count=0, oldest_age_minutes=None))
        )
        return handler

    @pytest.fixture
    def mock_container(
        self,
        mock_throughput_handler: MagicMock,
        mock_dead_letter_handler: MagicMock,
        mock_renderer: MagicMock,
    ) -> MagicMock:
        """Mock container that resolves handlers."""
        container = MagicMock()
        resolve_map = {
            EventsThroughputWidgetHandler: mock_throughput_handler,
            DeadLetterCountWidgetHandler: mock_dead_letter_handler,
            PackageWidgetRenderer: mock_renderer,
        }
        container.resolve = AsyncMock(side_effect=resolve_map.get)
        return container

    @pytest.fixture
    def contributor(
        self,
        mock_throughput_handler: MagicMock,
        mock_dead_letter_handler: MagicMock,
        mock_renderer: MagicMock,
        mock_container: MagicMock,
    ) -> EventsAdminContributor:
        """Create contributor with mocked handlers and renderer."""
        contributor = EventsAdminContributor()
        contributor._throughput_handler = mock_throughput_handler
        contributor._dead_letter_handler = mock_dead_letter_handler
        contributor._renderer = mock_renderer
        return contributor

    @pytest.mark.asyncio
    async def test_render_widget_throughput(
        self, contributor: EventsAdminContributor, mock_throughput_handler: MagicMock
    ) -> None:
        """Render events_throughput widget dispatches to handler."""
        result = await contributor.render_widget("events_throughput", WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>widget</div>"
        mock_throughput_handler.get_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_render_widget_dead_letter(
        self,
        contributor: EventsAdminContributor,
        mock_dead_letter_handler: MagicMock,
    ) -> None:
        """Render dead_letter_count widget dispatches to handler."""
        result = await contributor.render_widget("dead_letter_count", WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert vm.body == "<div>widget</div>"
        mock_dead_letter_handler.get_data.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_render_unknown_widget(
        self, contributor: EventsAdminContributor
    ) -> None:
        """Unknown widget name returns WidgetNotFoundError."""
        result = await contributor.render_widget("nonexistent", WidgetParams())
        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)
        assert error.contributor_name == "events"
        assert error.widget_name == "nonexistent"

    def test_get_dashboard_widgets(self, contributor: EventsAdminContributor) -> None:
        """Contributor returns two dashboard widgets."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 2
        names = {w.name for w in widgets}
        assert names == {"events_throughput", "dead_letter_count"}

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
    "TestDeadLetterCountWidgetHandler",
    "TestEventsAdminContributor",
    "TestEventsThroughputWidgetHandler",
]
