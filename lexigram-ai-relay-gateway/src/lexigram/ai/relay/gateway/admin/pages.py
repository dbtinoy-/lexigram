"""Management pages for the relay gateway admin contributor.

Pages are instantiated by the admin runtime from dotted-path handlers;
dependencies are resolved from the DI container.  Every page renders an
explicit unavailable state when a dependency is missing and returns
structured ``PageContent`` that the admin host renders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService
from lexigram.contracts.admin import PageContent, PaginationContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    Stat,
    StatContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.ai.relay import (
    RelayChannelStoreProtocol,
    RelayGatewayError,
    RelayPolicyStoreProtocol,
    TimeWindow,
)
from lexigram.logging import get_logger
from lexigram.primitives import clock

logger = get_logger(__name__)

_DEFAULT_WINDOW_MINUTES = 60
_PAGE_SIZE = 20


@dataclass(frozen=True, slots=True)
class _PageContext:
    """Request-derived pagination parameters."""

    page: int
    page_size: int
    minutes: int


class RelayGatewayOverviewPage:
    """Management page at /admin/relay-gateway/overview."""

    def __init__(
        self,
        health: RelayHealthService | None = None,
        controls: RelayControlsService | None = None,
        metrics: RelayMetricsService | None = None,
    ) -> None:
        self._health = health
        self._controls = controls
        self._metrics = metrics

    async def handle(self, request: Any) -> PageContent:
        """Render channel health, converter diagnostics, and stream count.

        Args:
            request: The starlette request.

        Returns:
            Structured stat grid for the overview page.
        """
        channel_count = "N/A"
        healthy_count = "N/A"
        active_streams = "N/A"
        converter = "N/A"

        if self._health is not None:
            try:
                snapshots = await self._health.channel_health()
                channel_count = str(len(snapshots))
                healthy_count = str(sum(1 for s in snapshots if s.status == "healthy"))
            except RelayGatewayError as exc:
                logger.warning("relay_page.overview.health_failed", error=str(exc))
            try:
                diagnostics = await self._health.registry_diagnostics()
                converter = diagnostics.converter_id
            except RelayGatewayError as exc:
                logger.warning("relay_page.overview.diagnostics_failed", error=str(exc))

        if self._controls is not None:
            active_streams = str(len(self._controls.active_streams()))

        return PageContent(
            title="Relay Gateway Overview",
            body=StatContent(
                stats=(
                    Stat(label="Channels", value=channel_count, icon="server"),
                    Stat(label="Healthy", value=healthy_count, icon="heart-pulse"),
                    Stat(label="Active Streams", value=active_streams, icon="radio"),
                    Stat(label="Converter", value=converter, icon="cpu"),
                )
            ),
        )


class RelayGatewayRoutesPage:
    """Management page at /admin/relay-gateway/routes."""

    def __init__(
        self,
        metrics: RelayMetricsService | None = None,
    ) -> None:
        self._metrics = metrics

    async def handle(self, request: Any) -> PageContent:
        """Render paginated per-route metrics.

        Args:
            request: The starlette request; accepts ``page``,
                ``page_size``, and ``minutes`` query parameters.

        Returns:
            Paginated routes table content.
        """
        ctx = _parse_pagination(request)
        if self._metrics is None:
            return PageContent(
                title="Relay Routes",
                body=EmptyContent(
                    title="Route Metrics Unavailable",
                    message="Route metrics service is not registered.",
                    icon="alert-triangle",
                ),
            )
        window = TimeWindow(
            start=clock.now() - timedelta(minutes=ctx.minutes),
            end=clock.now(),
        )
        try:
            rows = await self._metrics.route_metrics(window)
        except RelayGatewayError as exc:
            return PageContent(
                title="Relay Routes",
                body=EmptyContent(
                    title="Route Metrics Error",
                    message=exc.message,
                    icon="alert-triangle",
                ),
            )
        start = (ctx.page - 1) * ctx.page_size
        visible = rows[start : start + ctx.page_size]
        if not visible:
            return PageContent(
                title="Relay Routes",
                body=EmptyContent(
                    title="No Route Activity",
                    message="No route activity in this window.",
                    icon="inbox",
                ),
            )
        table_rows = tuple(
            (
                TableCell(r.source.value),
                TableCell(r.target.value),
                TableCell(str(r.request_count)),
                TableCell(str(r.unsupported_count)),
                TableCell(str(r.stream_failure_count)),
                TableCell(r.quality.value),
            )
            for r in visible
        )
        return PageContent(
            title="Relay Routes",
            body=TableContent(
                columns=(
                    "Route",
                    "Target",
                    "Requests",
                    "Unsupported",
                    "Stream Failures",
                    "Quality",
                ),
                rows=table_rows,
            ),
            pagination=PaginationContent(
                page=ctx.page,
                total=len(rows),
                per_page=ctx.page_size,
                base_url=str(request.url).split("?")[0],
            ),
        )


class RelayGatewayStreamsPage:
    """Management page at /admin/relay-gateway/streams."""

    def __init__(
        self,
        controls: RelayControlsService | None = None,
    ) -> None:
        self._controls = controls

    async def handle(self, request: Any) -> PageContent:
        """Render in-flight streams, oldest first.

        Args:
            request: The starlette request.

        Returns:
            Streams table content.
        """
        if self._controls is None:
            return PageContent(
                title="Relay Streams",
                body=EmptyContent(
                    title="Controls Service Unavailable",
                    message="Controls service is not registered.",
                    icon="alert-triangle",
                ),
            )
        streams = self._controls.active_streams()
        if not streams:
            return PageContent(
                title="Relay Streams",
                body=EmptyContent(
                    title="No Streams",
                    message="No streams in flight.",
                    icon="inbox",
                ),
            )
        rows = tuple(
            (
                TableCell(s.stream_id),
                TableCell(s.channel),
                TableCell(s.model),
                TableCell(s.request_id),
                TableCell(s.started_at.strftime("%Y-%m-%d %H:%M:%S")),
            )
            for s in streams
        )
        return PageContent(
            title="Relay Streams",
            body=TableContent(
                columns=("Stream ID", "Channel", "Model", "Request", "Started"),
                rows=rows,
            ),
        )


class RelayGatewaySettingsPage:
    """Management page at /admin/relay-gateway/settings."""

    def __init__(
        self,
        policy: RelayPolicyStoreProtocol | None = None,
    ) -> None:
        self._policy = policy

    async def handle(self, request: Any) -> PageContent:
        """Render the runtime routing policy.

        Args:
            request: The starlette request.

        Returns:
            Policy limits and allowlists table content.
        """
        if self._policy is None:
            return PageContent(
                title="Relay Settings",
                body=EmptyContent(
                    title="Policy Store Unavailable",
                    message="Policy store is not registered.",
                    icon="alert-triangle",
                ),
            )
        snapshot = await self._policy.load()
        details = (
            ("Media Schemes", ", ".join(sorted(snapshot.media_allowed_schemes)) or "-"),
            ("Media Hosts", ", ".join(sorted(snapshot.media_allowed_hosts)) or "-"),
            ("Max Request Bytes", str(snapshot.max_request_bytes)),
            ("Max Stream Seconds", f"{snapshot.max_stream_seconds:.0f}"),
        )
        rows = tuple(
            (TableCell(name), TableCell("enabled" if enabled else "drained"))
            for name, enabled in snapshot.enabled_channels.items()
        ) + tuple((TableCell(label), TableCell(value)) for label, value in details)
        return PageContent(
            title="Relay Settings",
            body=TableContent(columns=("Property", "Value"), rows=rows),
        )


class RelayGatewayChannelsPage:
    """Management page at /admin/relay-gateway/channels."""

    def __init__(
        self,
        store: RelayChannelStoreProtocol | None = None,
    ) -> None:
        self._store = store

    async def handle(self, request: Any) -> PageContent:
        """Render durable channel rows from the channel store.

        Args:
            request: The starlette request.

        Returns:
            Read-only channel table content, or an explicit note when
            the store is not registered or holds no channels.
        """
        if self._store is None:
            return PageContent(
                title="Relay Channels",
                body=EmptyContent(
                    title="Channel Store Unavailable",
                    message="Channel store is not registered.",
                    icon="alert-triangle",
                ),
            )
        snapshots = await self._store.list_channels()
        if not snapshots:
            return PageContent(
                title="Relay Channels",
                body=EmptyContent(
                    title="No Channels",
                    message="No channels stored.",
                    icon="inbox",
                ),
            )
        rows = tuple(
            (
                TableCell(s.channel.name),
                TableCell(s.channel.target_format.value),
                TableCell(", ".join(s.channel.models)),
                TableCell(str(s.channel.priority)),
                TableCell("enabled" if s.channel.enabled else "drained"),
                TableCell(str(s.revision)),
            )
            for s in snapshots
        )
        return PageContent(
            title="Relay Channels",
            body=TableContent(
                columns=("Name", "Format", "Models", "Priority", "State", "Revision"),
                rows=rows,
            ),
        )


def _parse_pagination(request: Any) -> _PageContext:
    """Parse pagination query parameters with safe defaults."""
    params = getattr(request, "query_params", None)
    raw = dict(params) if params is not None else {}

    def _int(name: str, default: int, lo: int, hi: int) -> int:
        try:
            value = int(raw.get(name, default))
        except (TypeError, ValueError):
            return default
        return max(lo, min(hi, value))

    page = _int("page", 1, 1, 1_000_000)
    page_size = _int("page_size", _PAGE_SIZE, 1, 100)
    minutes = _int("minutes", _DEFAULT_WINDOW_MINUTES, 1, 24 * 60)
    return _PageContext(page=page, page_size=page_size, minutes=minutes)
