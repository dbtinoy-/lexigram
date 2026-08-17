"""Admin dashboard widgets for the relay gateway.

Defines the widget catalog and the content builders behind each widget.
A missing (None) service renders an explicit unavailable
``MessageContent`` state rather than failing the whole dashboard.
"""

from __future__ import annotations

from datetime import timedelta

from lexigram.ai.relay.gateway.operations.controls import (
    PERMISSION_READ,
    RelayControlsService,
)
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService
from lexigram.contracts.admin.types import (
    DashboardWidgetDefinition,
    WidgetCategory,
    WidgetKind,
    WidgetParams,
    WidgetSize,
)
from lexigram.contracts.admin.widget_content import (
    MessageContent,
    TableCell,
    TableContent,
    Tone,
    WidgetContent,
)
from lexigram.contracts.ai.relay import RelayGatewayError, TimeWindow
from lexigram.primitives import clock

__all__ = [
    "WIDGETS",
    "active_streams_content",
    "channel_health_content",
    "route_activity_content",
]

WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="channel_health",
        title="Channel Health",
        contributor="relay-gateway",
        render_endpoint="/admin/relay-gateway/widgets/channel_health",
        size=WidgetSize.LARGE,
        category=WidgetCategory.HEALTH,
        view_kind=WidgetKind.TABLE,
        refresh_interval_seconds=15,
        permission=PERMISSION_READ,
        icon="heart-pulse",
        description="Per-channel health snapshots from probe status.",
    ),
    DashboardWidgetDefinition(
        name="route_activity",
        title="Route Activity",
        contributor="relay-gateway",
        render_endpoint="/admin/relay-gateway/widgets/route_activity",
        size=WidgetSize.LARGE,
        category=WidgetCategory.METRICS,
        view_kind=WidgetKind.TABLE,
        refresh_interval_seconds=30,
        permission=PERMISSION_READ,
        icon="activity",
        description="Per-route conversion and failure metrics.",
    ),
    DashboardWidgetDefinition(
        name="active_streams",
        title="Active Streams",
        contributor="relay-gateway",
        render_endpoint="/admin/relay-gateway/widgets/active_streams",
        size=WidgetSize.MEDIUM,
        category=WidgetCategory.METRICS,
        view_kind=WidgetKind.TABLE,
        refresh_interval_seconds=10,
        permission=PERMISSION_READ,
        icon="radio",
        description="In-flight upstream streams, oldest first.",
    ),
)


async def channel_health_content(
    health: RelayHealthService | None,
    params: WidgetParams,
) -> WidgetContent:
    """Render per-channel health as a status table.

    Args:
        health: Resolved health service, or None when unavailable at boot.
        params: Typed widget parameters (unused for this widget).

    Returns:
        TableContent of channel snapshots, or an unavailable message.
    """
    del params
    if health is None:
        return MessageContent(
            text="Channel health unavailable; health service not resolved.",
            tone=Tone.INFO,
        )
    snapshots = await health.channel_health()
    rows = tuple(
        (
            TableCell(text=snap.channel),
            TableCell(text=snap.target.value),
            TableCell(text=snap.status, tone=_status_tone(snap.status)),
            TableCell(text=str(snap.model_count)),
            TableCell(text=_ms(snap.latency_ms_p50)),
            TableCell(text=_details(snap.detail_code)),
        )
        for snap in snapshots
    )
    return TableContent(
        columns=(
            "Channel",
            "Target",
            "Status",
            "Models",
            "P50",
            "Detail",
        ),
        rows=rows,
        empty_message="No channels configured.",
    )


async def route_activity_content(
    metrics: RelayMetricsService | None,
    params: WidgetParams,
) -> WidgetContent:
    """Render routed metrics for the widget window.

    Args:
        metrics: Resolved metrics service, or None when unavailable at boot.
        params: Typed widget parameters carrying the time window.

    Returns:
        TableContent of route metrics, or an unavailable message.
    """
    if metrics is None:
        return MessageContent(
            text="Route metrics service is unavailable.",
            tone=Tone.INFO,
        )
    window = TimeWindow(
        start=clock.now() - timedelta(minutes=params.time_window_minutes),
        end=clock.now(),
    )
    try:
        routes = await metrics.route_metrics(window)
    except RelayGatewayError as exc:
        return MessageContent(text=exc.message, tone=Tone.INFO)
    rows = tuple(
        (
            TableCell(text=route.source.value),
            TableCell(text=route.target.value),
            TableCell(text=str(route.request_count)),
            TableCell(text=str(route.unsupported_count)),
            TableCell(text=str(route.stream_failure_count)),
            TableCell(
                text=route.quality.value,
                tone=_quality_tone(route.quality.value),
            ),
        )
        for route in routes
    )
    return TableContent(
        columns=(
            "Route",
            "Target",
            "Requests",
            "Unsupported",
            "Stream Failures",
            "Quality",
        ),
        rows=rows,
        empty_message="No route activity in this window.",
    )


async def active_streams_content(
    controls: RelayControlsService | None,
    params: WidgetParams,
) -> WidgetContent:
    """Render the in-flight stream registry.

    Args:
        controls: Resolved controls service, or None when unavailable at boot.
        params: Typed widget parameters (unused for this widget).

    Returns:
        TableContent of active streams, or an unavailable message.
    """
    del params
    if controls is None:
        return MessageContent(
            text="Controls service is unavailable.",
            tone=Tone.INFO,
        )
    streams = controls.active_streams()
    if not streams:
        return MessageContent(text="No streams in flight.")
    rows = tuple(
        (
            TableCell(text=s.stream_id),
            TableCell(text=s.channel),
            TableCell(text=s.model),
            TableCell(text=_iso(s.started_at)),
        )
        for s in streams
    )
    return TableContent(
        columns=("Stream", "Channel", "Model", "Started"),
        rows=rows,
    )


def _status_tone(status: str) -> Tone:
    """Map a channel health status to a content tone."""
    tones = {
        "healthy": Tone.SUCCESS,
        "degraded": Tone.WARNING,
        "unavailable": Tone.DEFAULT,
        "failed": Tone.DANGER,
    }
    return tones.get(status, Tone.DEFAULT)


def _quality_tone(quality: str) -> Tone:
    """Map a conversion quality to a content tone."""
    tones = {
        "native": Tone.SUCCESS,
        "preserved": Tone.INFO,
        "lossless": Tone.SUCCESS,
        "lossy": Tone.WARNING,
        "discouraged": Tone.DANGER,
    }
    return tones.get(quality, Tone.DEFAULT)


def _ms(value: float | None) -> str:
    """Format a latency value as milliseconds."""
    return f"{value:.1f} ms" if value is not None else "-"


def _iso(dt: object) -> str:
    """Format a datetime for display."""
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _details(detail_code: str | None) -> str:
    """Humanize the machine-readable detail code."""
    if detail_code is None:
        return "-"
    return detail_code.replace("_", " ")
