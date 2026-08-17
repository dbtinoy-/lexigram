"""Tests for the relay gateway route metrics service.

Covers ``RelayMetricsService`` window filtering, per-route and
per-loss-code aggregation, stable empty results, and registry
diagnostics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.ai.relay.gateway.operations.metrics import (
    RelayMetricsService,
    RelayRouteEvent,
    RelayRouteEventSourceProtocol,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayFormat,
    RelayGatewayError,
    RelayRegistryDiagnostics,
    RelayRegistryProtocol,
    TimeWindow,
)

T0 = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
T1 = datetime(2026, 8, 1, 10, 30, 0, tzinfo=UTC)


def at(minutes: int) -> datetime:
    """Return a timestamp inside the test window."""
    return T0 + timedelta(minutes=minutes)


def completed(src: RelayFormat, tgt: RelayFormat) -> RelayRouteEvent:
    """A request-completed event inside the window."""
    return RelayRouteEvent(
        kind="request_completed",
        source=src,
        target=tgt,
        occurred_at=at(1),
    )


class StubEventSource(RelayRouteEventSourceProtocol):
    """Event source shaped with a fixed tuple."""

    def __init__(self, events: tuple[RelayRouteEvent, ...]) -> None:
        self._events = events

    async def events(self, window: TimeWindow) -> tuple[RelayRouteEvent, ...]:
        """Return the fixed event tuple."""
        return self._events


class FakeRegistry(RelayRegistryProtocol):
    """Stub registry exposing routes, mappers, and version."""

    def mapper(self, source: RelayFormat, target: RelayFormat) -> None:
        """Return a mapper for the pair, always ``None`` here."""
        return None

    def converter_routes(self) -> tuple[tuple[RelayFormat, RelayFormat], ...]:
        """Return the supported route pairs."""
        return (
            (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            (RelayFormat.CLAUDE, RelayFormat.GEMINI),
        )

    def mapper_ids(self) -> tuple[str, ...]:
        """Return the registered mapper ids."""
        return ("claude", "gemini", "openai_chat")

    def converter_version(self) -> str:
        """Return the fixed converter version."""
        return "1.0.0"

    def route_quality(
        self,
        source: RelayFormat,
        target: RelayFormat,
    ) -> ConversionQuality:
        """Return the matrix quality for the pair."""
        return ConversionQuality.FAIR


def make_service(
    *events: RelayRouteEvent,
    converter: RelayRegistryProtocol | None = None,
) -> RelayMetricsService:
    """Build a metrics service over the given events."""
    return RelayMetricsService(
        events=StubEventSource(events),
        converter=converter,
    )


class TestMetrics:
    async def test_groups_by_route(self) -> None:
        service = make_service(
            completed(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            completed(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            completed(RelayFormat.GEMINI, RelayFormat.OPENAI_CHAT),
        )
        rows = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        by_route = {(row.source, row.target): row for row in rows}
        assert by_route[(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE)].request_count == 2
        assert by_route[(RelayFormat.GEMINI, RelayFormat.OPENAI_CHAT)].request_count == 1

    async def test_loss_counts_by_code(self) -> None:
        service = make_service(
            completed(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            RelayRouteEvent(
                kind="conversion_loss",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(2),
                loss_code="unsupported_option",
            ),
            RelayRouteEvent(
                kind="conversion_loss",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(3),
                loss_code="unsupported_option",
            ),
        )
        (row,) = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert row.loss_counts == {"unsupported_option": 2}
        assert row.request_count == 1

    async def test_only_loss_codes_are_counted(self) -> None:
        service = make_service(
            RelayRouteEvent(
                kind="conversion_loss",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(2),
                loss_code=None,
            ),
        )
        (row,) = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert row.loss_counts == {}

    async def test_unsupported_and_stream_failures(self) -> None:
        service = make_service(
            RelayRouteEvent(
                kind="unsupported_feature",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(1),
            ),
            RelayRouteEvent(
                kind="stream_cancelled",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(2),
            ),
            RelayRouteEvent(
                kind="stream_timeout",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(3),
            ),
            RelayRouteEvent(
                kind="stream_truncated",
                source=RelayFormat.OPENAI_CHAT,
                target=RelayFormat.CLAUDE,
                occurred_at=at(4),
            ),
        )
        (row,) = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert row.unsupported_count == 1
        assert row.stream_failure_count == 3

    async def test_filters_events_by_window(self) -> None:
        early = RelayRouteEvent(
            kind="request_completed",
            source=RelayFormat.OPENAI_CHAT,
            target=RelayFormat.CLAUDE,
            occurred_at=T0,
        )
        late = RelayRouteEvent(
            kind="request_completed",
            source=RelayFormat.OPENAI_CHAT,
            target=RelayFormat.CLAUDE,
            occurred_at=T1,
        )
        service = make_service(
            early,
            completed(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            late,
        )
        (row,) = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert row.request_count == 1

    async def test_empty_event_source_returns_stable_empty(self) -> None:
        service = make_service()
        assert (
            await service.route_metrics(window=TimeWindow(start=T0, end=T1))
            == []
        )

    async def test_quality_reflects_route_matrix(self) -> None:
        service = make_service(
            completed(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            converter=FakeRegistry(),
        )
        (row,) = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert row.quality == ConversionQuality.FAIR

    async def test_route_metrics_carry_converter_id_when_known(self) -> None:
        service = make_service(
            completed(RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE),
            converter=FakeRegistry(),
        )
        (row,) = await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert row.converter_id == "openai_chat_to_claude"


class TestMetricsDiagnostics:
    async def test_registry_diagnostics_shape(self) -> None:
        service = make_service(converter=FakeRegistry())
        diagnostics = await service.registry_diagnostics()
        assert isinstance(diagnostics, RelayRegistryDiagnostics)
        assert diagnostics.converter_version == "1.0.0"
        assert diagnostics.mapper_ids == ("claude", "gemini", "openai_chat")
        assert (RelayFormat.OPENAI_CHAT, RelayFormat.CLAUDE) in (
            diagnostics.supported_routes
        )

    async def test_missing_converter_is_failed_dependency(self) -> None:
        service = make_service(converter=None)
        with pytest.raises(RelayGatewayError) as exc:
            await service.registry_diagnostics()
        assert exc.value.code == "DEPENDENCY_UNAVAILABLE"

    async def test_missing_event_source_is_failed_dependency(self) -> None:
        service = RelayMetricsService(events=None, converter=FakeRegistry())
        with pytest.raises(RelayGatewayError) as exc:
            await service.route_metrics(window=TimeWindow(start=T0, end=T1))
        assert exc.value.code == "DEPENDENCY_UNAVAILABLE"