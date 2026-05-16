"""Management pages for the relay gateway admin contributor.

Pages are instantiated by the admin runtime from dotted-path handlers;
dependencies are resolved from the DI container.  Every page renders an
explicit unavailable state when a dependency is missing and never
injects unescaped values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from starlette.responses import HTMLResponse

from lexigram.ai.relay.gateway.operations.controls import RelayControlsService
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService
from lexigram.contracts.ai.relay import (
    RelayChannelStoreProtocol,
    RelayGatewayError,
    RelayPolicyStoreProtocol,
    TimeWindow,
)
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

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

    async def handle(self, request: Any) -> HTMLResponse:
        """Render channel health, converter diagnostics, and stream count.

        Args:
            request: The starlette request.

        Returns:
            Fully rendered overview page HTML.
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

        page = [
            el(
                "h1",
                "Relay Gateway Overview",
                class_="text-2xl font-bold text-[var(--foreground)]",
            ),
            el(
                "p",
                "Operational status of the gateway channels and converters.",
                class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
            ),
            Divider(),
            Grid(
                StatCard(label="Channels", value=channel_count, icon="server"),
                StatCard(label="Healthy", value=healthy_count, icon="heart-pulse"),
                StatCard(
                    label="Active Streams",
                    value=str(active_streams),
                    icon="radio",
                ),
                StatCard(label="Converter", value=converter, icon="cpu"),
                cols={"default": 1, "lg": 4},
                gap=4,
            ),
            _dependency_card("health", self._health is not None),
            _dependency_card("controls", self._controls is not None),
            await _channel_health_card(self._health),
            el("div", class_="p-6"),
        ]
        html = render_to_string(el("div", *page))
        return HTMLResponse(html)


class RelayGatewayRoutesPage:
    """Management page at /admin/relay-gateway/routes."""

    def __init__(
        self,
        metrics: RelayMetricsService | None = None,
    ) -> None:
        self._metrics = metrics

    async def handle(self, request: Any) -> HTMLResponse:
        """Render paginated per-route metrics.

        Args:
            request: The starlette request; accepts ``page``,
                ``page_size``, and ``minutes`` query parameters.

        Returns:
            Paginated routes table HTML.
        """
        ctx = _parse_pagination(request)
        header = _build_header(
            "Relay Routes",
            "Per-route conversion counts, losses, and failures.",
        )
        if self._metrics is None:
            return HTMLResponse(
                str(header)
                + render_to_string(
                    el(
                        "p",
                        "Route metrics service is not registered.",
                        class_="text-sm text-[var(--muted-foreground)] p-6",
                    )
                )
            )
        window = TimeWindow(
            start=clock.now() - timedelta(minutes=ctx.minutes),
            end=clock.now(),
        )
        try:
            rows = await self._metrics.route_metrics(window)
        except RelayGatewayError as exc:
            return HTMLResponse(
                str(header)
                + render_to_string(
                    el(
                        "p",
                        exc.message,
                        class_="text-sm text-[var(--muted-foreground)] p-6",
                    )
                )
            )
        start = (ctx.page - 1) * ctx.page_size
        visible = rows[start : start + ctx.page_size]
        table_rows = [
            el(
                "tr",
                el("td", r.source.value, class_="py-1.5 pr-3 font-medium"),
                el("td", r.target.value, class_="py-1.5 pr-3"),
                el("td", str(r.request_count), class_="py-1.5 pr-3"),
                el("td", str(r.unsupported_count), class_="py-1.5 pr-3"),
                el("td", str(r.stream_failure_count), class_="py-1.5 pr-3"),
                el("td", r.quality.value, class_="py-1.5"),
            )
            for r in visible
        ]
        body_content = (
            render_to_string(
                el(
                    "table",
                    _thead(
                        (
                            "Route",
                            "Target",
                            "Requests",
                            "Unsupported",
                            "Stream Failures",
                            "Quality",
                        )
                    ),
                    el("tbody", *table_rows, class_="divide-y divide-[var(--border)]"),
                    class_="w-full",
                )
            )
            if table_rows
            else render_to_string(
                el(
                    "p",
                    "No route activity in this window.",
                    class_="text-sm text-[var(--muted-foreground)] py-4",
                )
            )
        )
        card = Card(
            title=f"Route Activity (last {ctx.minutes}m)",
            content=body_content,
        )
        return HTMLResponse(str(header) + render_to_string(card))


class RelayGatewayStreamsPage:
    """Management page at /admin/relay-gateway/streams."""

    def __init__(
        self,
        controls: RelayControlsService | None = None,
    ) -> None:
        self._controls = controls

    async def handle(self, request: Any) -> HTMLResponse:
        """Render in-flight streams, oldest first.

        Args:
            request: The starlette request.

        Returns:
            Streams table HTML.
        """
        header = _build_header(
            "Relay Streams",
            "In-flight upstream streams, oldest first.",
        )
        contents = [header]
        if self._controls is None:
            contents.append(
                el(
                    "p",
                    "Controls service is not registered.",
                    class_="text-sm text-[var(--muted-foreground)] p-6",
                )
            )
            return HTMLResponse(render_to_string(el("div", *contents)))
        streams = self._controls.active_streams()
        if not streams:
            contents.append(
                el(
                    "p",
                    "No streams in flight.",
                    class_="text-sm text-[var(--muted-foreground)] p-6",
                )
            )
        else:
            rows = [
                el(
                    "tr",
                    el("td", s.stream_id, class_="py-1.5 pr-3 font-mono text-xs"),
                    el("td", s.channel, class_="py-1.5 pr-3"),
                    el("td", s.model, class_="py-1.5 pr-3"),
                    el("td", s.request_id, class_="py-1.5 pr-3"),
                    el(
                        "td",
                        s.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                        class_="py-1.5",
                    ),
                )
                for s in streams
            ]
            contents.append(
                el(
                    "table",
                    _thead(("Stream ID", "Channel", "Model", "Request", "Started")),
                    el("tbody", *rows, class_="divide-y divide-[var(--border)]"),
                    class_="w-full",
                )
            )
        return HTMLResponse(render_to_string(el("div", *contents, class_="p-6")))


class RelayGatewaySettingsPage:
    """Management page at /admin/relay-gateway/settings."""

    def __init__(
        self,
        policy: RelayPolicyStoreProtocol | None = None,
    ) -> None:
        self._policy = policy

    async def handle(self, request: Any) -> HTMLResponse:
        """Render the runtime routing policy.

        Args:
            request: The starlette request.

        Returns:
            Policy limits and allowlists HTML.
        """
        header = _build_header(
            "Relay Settings",
            "Runtime routing policy enforced by the gateway.",
        )
        if self._policy is None:
            return HTMLResponse(
                str(header)
                + render_to_string(
                    el(
                        "p",
                        "Policy store is not registered.",
                        class_="text-sm text-[var(--muted-foreground)] p-6",
                    )
                )
            )
        snapshot = await self._policy.load()
        channel_list = el(
            "ul",
            *[
                _channel_item(name, enabled)
                for name, enabled in snapshot.enabled_channels.items()
            ],
            class_="divide-y divide-[var(--border)]",
        )
        details = [
            ("Media Schemes", ", ".join(sorted(snapshot.media_allowed_schemes)) or "-"),
            ("Media Hosts", ", ".join(sorted(snapshot.media_allowed_hosts)) or "-"),
            ("Max Request Bytes", str(snapshot.max_request_bytes)),
            ("Max Stream Seconds", f"{snapshot.max_stream_seconds:.0f}"),
        ]
        detail_rows = [
            el(
                "tr",
                el("td", label, class_="py-1.5 pr-3 font-medium"),
                el("td", value, class_="py-1.5"),
            )
            for label, value in details
        ]
        card = Card(
            title="Routing Policy",
            content=render_to_string(
                el(
                    "div",
                    el(
                        "h3",
                        "Channels",
                        class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                    ),
                    channel_list,
                    el(
                        "h3",
                        "Limits",
                        class_="text-sm font-semibold text-[var(--muted-foreground)] pt-4 pb-2",
                    ),
                    el(
                        "dl",
                        *[
                            el(
                                "div",
                                el(
                                    "dt",
                                    label,
                                    class_="text-sm font-semibold text-[var(--muted-foreground)] py-1",
                                ),
                                el("dd", value, class_="text-sm pb-2"),
                            )
                            for label, value in details
                        ],
                        class_="divide-y divide-[var(--border)]",
                    ),
                )
            ),
        )
        return HTMLResponse(str(header) + render_to_string(card))


class RelayGatewayChannelsPage:
    """Management page at /admin/relay-gateway/channels."""

    def __init__(
        self,
        store: RelayChannelStoreProtocol | None = None,
    ) -> None:
        self._store = store

    async def handle(self, request: Any) -> HTMLResponse:
        """Render durable channel rows from the channel store.

        Args:
            request: The starlette request.

        Returns:
            Read-only channel table HTML, or an explicit note when the
            store is not registered or holds no channels.
        """
        header = _build_header(
            "Relay Channels",
            "Durable channel rows managed through the channel store.",
        )
        if self._store is None:
            return HTMLResponse(
                str(header)
                + render_to_string(
                    el(
                        "p",
                        "Channel store is not registered.",
                        class_="text-sm text-[var(--muted-foreground)] p-6",
                    )
                )
            )
        snapshots = await self._store.list_channels()
        rows = [
            el(
                "tr",
                el("td", s.channel.name, class_="py-1.5 pr-3 font-medium"),
                el("td", s.channel.target_format.value, class_="py-1.5 pr-3"),
                el("td", ", ".join(s.channel.models), class_="py-1.5 pr-3"),
                el("td", str(s.channel.priority), class_="py-1.5 pr-3"),
                el(
                    "td",
                    "enabled" if s.channel.enabled else "drained",
                    class_="py-1.5 pr-3",
                ),
                el("td", str(s.revision), class_="py-1.5"),
            )
            for s in snapshots
        ]
        if not rows:
            return HTMLResponse(
                str(header)
                + render_to_string(
                    el(
                        "p",
                        "No channels stored.",
                        class_="text-sm text-[var(--muted-foreground)] p-6",
                    )
                )
            )
        card = Card(
            title="Channels",
            content=render_to_string(
                el(
                    "table",
                    _thead(
                        ("Name", "Format", "Models", "Priority", "State", "Revision")
                    ),
                    el("tbody", *rows, class_="divide-y divide-[var(--border)]"),
                    class_="w-full",
                )
            ),
        )
        return HTMLResponse(str(header) + render_to_string(card))


def _channel_item(name: str, enabled: bool) -> Any:
    """Render an escaped channel entry."""
    badge = el(
        "span",
        "enabled" if enabled else "drained",
        class_=(
            "inline-flex px-2 py-0.5 rounded text-xs font-medium "
            + ("bg-green-100 text-green-700" if enabled else "bg-red-100 text-red-700")
        ),
    )
    return el("li", name, badge, class_="flex items-center gap-2 py-1")


def _build_header(title: str, subtitle: str) -> str:
    """Build the shared page header HTML."""
    return render_to_string(
        el(
            "div",
            el("h1", title, class_="text-2xl font-bold text-[var(--foreground)]"),
            el(
                "p",
                subtitle,
                class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
            ),
        )
    )


def _dependency_card(name: str, available: bool) -> Any:
    """Render an explicit dependency availability note."""
    color = "bg-green-100 text-green-700" if available else "bg-red-100 text-red-700"
    return el(
        "div",
        el(
            "span",
            f"{name} service",
            class_=f"inline-block px-2 py-0.5 rounded text-xs font-medium {color}",
        ),
        class_="pt-4",
    )


def _thead(headers: tuple[str, ...]) -> Any:
    """Build a table header element."""
    return el(
        "thead",
        el(
            "tr",
            *[
                el(
                    "th",
                    h,
                    class_=(
                        "text-left text-xs font-semibold "
                        "text-[var(--muted-foreground)] uppercase tracking-wider pb-1 pr-3"
                    ),
                    scope_="col",
                )
                for h in headers
            ],
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


def _status_badge(status: str) -> Any:
    """Render an escaped status badge."""
    color = {
        "healthy": "bg-green-100 text-green-700",
        "degraded": "bg-yellow-100 text-yellow-700",
        "unavailable": "bg-gray-100 text-gray-700",
        "failed": "bg-red-100 text-red-700",
    }.get(status, "bg-gray-100 text-gray-700")
    return el(
        "span",
        status,
        class_=f"inline-flex px-2 py-0.5 rounded text-xs font-medium {color}",
    )


async def _channel_health_card(health: RelayHealthService | None) -> Any:
    """Render the channel health table, or an explicit unavailable note.

    Args:
        health: The health service, or None if unavailable.

    Returns:
        The table element, or an unavailable note.
    """
    if health is None:
        return _dependency_card("health", False)
    rows: list[Any] = []
    for row in await health.channel_health():
        detail = row.detail_code or "-"
        rows.append(
            el(
                "tr",
                el("td", row.channel, class_="py-1.5 pr-3 font-medium"),
                el("td", row.target.value, class_="py-1.5 pr-3"),
                el(
                    "td",
                    _status_badge(row.status),
                    class_="py-1.5 pr-3",
                ),
                el("td", str(row.model_count), class_="py-1.5 pr-3"),
                el(
                    "td",
                    (
                        f"{row.latency_ms_p50:.1f} ms"
                        if row.latency_ms_p50 is not None
                        else "-"
                    ),
                    class_="py-1.5 pr-3",
                ),
                el("td", detail, class_="py-1.5"),
            )
        )
    if not rows:
        return el(
            "p",
            "No channel health snapshots available.",
            class_="text-sm text-[var(--muted-foreground)] py-4",
        )
    return el(
        "div",
        el(
            "h2",
            "Channel Health",
            class_="text-lg font-semibold text-[var(--foreground)] pt-6 pb-2",
        ),
        el(
            "table",
            _thead(("Channel", "Target", "Status", "Models", "Latency", "Detail")),
            el("tbody", *rows, class_="divide-y divide-[var(--border)]"),
            class_="w-full",
        ),
    )
