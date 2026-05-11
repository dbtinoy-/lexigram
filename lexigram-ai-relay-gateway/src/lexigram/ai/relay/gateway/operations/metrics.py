"""Route metrics aggregation for the relay gateway operations surface.

``RelayMetricsService`` turns routed operational events into stable
``RelayRouteMetrics`` rows grouped by directed route and time window,
counting conversion losses from stable codes.  Registry diagnostics and
package-version reporting stay import-free for mapper modules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayFormat,
    RelayGatewayError,
    RelayRegistryDiagnostics,
    RelayRegistryProtocol,
    RelayRouteMetrics,
    TimeWindow,
)

__all__ = [
    "CONVERTER_ID",
    "RelayMetricsService",
    "RelayRouteEvent",
    "RelayRouteEventSourceProtocol",
    "RouteMetricEventKind",
]

CONVERTER_ID = "relay-converter"
"""Diagnostics identifier for the built-in relay converter."""

RouteMetricEventKind = Literal[
    "request_completed",
    "conversion_loss",
    "unsupported_feature",
    "stream_cancelled",
    "stream_timeout",
    "stream_truncated",
]


@dataclass(frozen=True, slots=True)
class RelayRouteEvent:
    """One operational event feeding route metric aggregation.

    Attributes:
        kind: Event kind; only ``conversion_loss`` events carry a code.
        source: Source wire format of the route.
        target: Target wire format of the route.
        occurred_at: When the event happened (UTC).
        loss_code: Stable conversion loss code for ``conversion_loss``
            events; ignored for every other kind.
    """

    kind: RouteMetricEventKind
    source: RelayFormat
    target: RelayFormat
    occurred_at: datetime
    loss_code: str | None = None


@runtime_checkable
class RelayRouteEventSourceProtocol(Protocol):
    """Provides operational events inside a bounded window."""

    async def events(self, window: TimeWindow) -> Sequence[RelayRouteEvent]:
        """Return the events observed inside *window*.

        Args:
            window: Bounded aggregation window.

        Returns:
            Events bounded to the window; an empty sequence means no
            activity, never a failed lookup.
        """
        ...


class RelayMetricsService:
    """Aggregate route metrics for the admin operations surface.

    Counts, per directed route and window:

    - ``request_count`` from ``request_completed`` events.
    - ``loss_counts`` from ``conversion_loss`` codes (never free-form
      messages).
    - ``unsupported_count`` from ``unsupported_feature`` events.
    - ``stream_failure_count`` from stream
      cancelled/timeout/truncated events.

    A missing event source is a failed dependency; an empty source
    yields a stable empty result, never a fabricated zero-count row.
    """

    def __init__(
        self,
        events: RelayRouteEventSourceProtocol | None,
        converter: RelayRegistryProtocol | None = None,
        registration_errors: tuple[str, ...] = (),
    ) -> None:
        """Bind the metrics service to its dependencies.

        Args:
            events: Operational event source for route aggregation.
                ``None`` makes ``route_metrics`` a failed dependency.
            converter: Optional converter registry used for route-quality
                and diagnostics. ``None`` makes
                ``registry_diagnostics`` a failed dependency.
            registration_errors: Registrations that failed at wiring
                time, surfaced verbatim in diagnostics.
        """
        self._events = events
        self._converter = converter
        self._registration_errors = registration_errors

    async def route_metrics(self, window: TimeWindow) -> Sequence[RelayRouteMetrics]:
        """Return per-route metrics aggregated inside *window*.

        Args:
            window: Bounded aggregation window.

        Returns:
            One row per route that saw activity within the window.

        Raises:
            RelayGatewayError: With ``DEPENDENCY_UNAVAILABLE`` when no
                event source is registered.
        """
        if self._events is None:
            raise RelayGatewayError(
                code="DEPENDENCY_UNAVAILABLE",
                message="relay route event source is not registered",
                status_code=503,
                request_id="",
            )
        events = await self._events.events(window)
        buckets: dict[tuple[RelayFormat, RelayFormat], list[RelayRouteEvent]] = {}
        for event in events:
            if window.start < event.occurred_at < window.end:
                key = (event.source, event.target)
                buckets.setdefault(key, []).append(event)
        rows: list[RelayRouteMetrics] = []
        for (source, target), route_events in sorted(buckets.items()):
            rows.append(
                RelayRouteMetrics(
                    source=source,
                    target=target,
                    quality=self._quality(source, target),
                    request_count=sum(
                        1 for e in route_events if e.kind == "request_completed"
                    ),
                    loss_counts=self._losses(route_events),
                    unsupported_count=sum(
                        1 for e in route_events if e.kind == "unsupported_feature"
                    ),
                    stream_failure_count=sum(
                        1
                        for e in route_events
                        if e.kind
                        in ("stream_cancelled", "stream_timeout", "stream_truncated")
                    ),
                    converter_id=self._converter_id(source, target),
                    window_start=window.start,
                    window_end=window.end,
                )
            )
        return rows

    async def registry_diagnostics(self) -> RelayRegistryDiagnostics:
        """Return converter capability diagnostics.

        Returns:
            Converter identifier, version, mapper ids, supported route
            pairs, and startup registration failures.

        Raises:
            RelayGatewayError: With ``DEPENDENCY_UNAVAILABLE`` when no
                converter registry is registered.
        """
        if self._converter is None:
            raise RelayGatewayError(
                code="DEPENDENCY_UNAVAILABLE",
                message="converter registry is not registered",
                status_code=503,
                request_id="",
            )
        return RelayRegistryDiagnostics(
            converter_id=CONVERTER_ID,
            converter_version=self._converter.converter_version(),
            mapper_ids=self._converter.mapper_ids(),
            supported_routes=self._converter.converter_routes(),
            registration_errors=self._registration_errors,
        )

    @staticmethod
    def _losses(
        route_events: Sequence[RelayRouteEvent],
    ) -> Mapping[str, int]:
        """Count conversion losses by stable code."""
        counts: dict[str, int] = {}
        for event in route_events:
            if event.kind == "conversion_loss" and event.loss_code:
                counts[event.loss_code] = counts.get(event.loss_code, 0) + 1
        return counts

    def _quality(self, source: RelayFormat, target: RelayFormat) -> ConversionQuality:
        """Return the route quality from the converter matrix."""
        if self._converter is None:
            return ConversionQuality.DISCOURAGED
        return self._converter.route_quality(source, target)

    def _converter_id(self, source: RelayFormat, target: RelayFormat) -> str | None:
        """Return the route converter identifier, when known."""
        if self._converter is None:
            return None
        return f"{source.value}_to_{target.value}"
