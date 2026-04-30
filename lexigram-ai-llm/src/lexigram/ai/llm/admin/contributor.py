"""Admin contributor for lexigram-ai-llm — surfaces token usage, provider
status, and error-rate widgets into the Lexigram admin dashboard.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import (
    AdminError,
    HealthCheckNotFoundError,
    WidgetNotFoundError,
)
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    WidgetCategory,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.ai.routing import InferenceLoggerProtocol, LLMRouterProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.result import Err, Ok, Result
from lexigram.ui import el

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="token_usage",
        title="Token Usage",
        contributor="ai-llm",
        render_endpoint="/admin/ai-llm/widgets/token_usage",
        size=WidgetSize.LARGE,
        category=WidgetCategory.METRICS,
        description="Prompt and completion token consumption across all providers.",
    ),
    DashboardWidgetDefinition(
        name="provider_status",
        title="Provider Status",
        contributor="ai-llm",
        render_endpoint="/admin/ai-llm/widgets/provider_status",
        size=WidgetSize.SMALL,
        category=WidgetCategory.HEALTH,
        description="Reachability and latency for each configured LLM provider.",
    ),
    DashboardWidgetDefinition(
        name="error_rate",
        title="Error Rate",
        contributor="ai-llm",
        render_endpoint="/admin/ai-llm/widgets/error_rate",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        description="LLM API error rate over the last rolling window.",
    ),
)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="AI",
        url="/admin/ai/llm",
        icon="sparkles",
        group="ai",
        order=50,
        children=(
            NavigationContribution(
                label="Usage",
                url="/admin/ai/llm/usage",
                icon="bar-chart-2",
                group="ai",
                order=10,
            ),
            NavigationContribution(
                label="Providers",
                url="/admin/ai/llm/providers",
                icon="server",
                group="ai",
                order=20,
            ),
        ),
    ),
)

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="ai.llm.provider",
        contributor="ai-llm",
        component="LLM Provider",
        check_endpoint="/admin/ai-llm/health/provider",
        description="Verifies the primary LLM provider is reachable and responding.",
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="rotate_api_key",
        title="Rotate API Key",
        contributor="ai-llm",
        handler="lexigram.ai.llm.admin.actions:rotate_api_key",
        icon="refresh-cw",
        confirmation_message="This will invalidate the current API key. Are you sure?",
        destructive=True,
        category="security",
    ),
)


class LlmAdminContributor(BaseAdminContributor):
    """Admin contributor for the lexigram-ai-llm package."""

    name = "ai-llm"
    display_name = "AI / LLM"
    group = "ai"
    icon = "sparkles"
    priority = 50

    def __init__(self) -> None:
        self._container: ContainerResolverProtocol | None = None

    async def on_admin_boot(self, container: ContainerResolverProtocol) -> None:
        self._container = container

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return list(_ACTIONS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="llm_overview",
                title="LLM Overview",
                contributor="ai-llm",
                route_path="/ai/llm",
                handler="lexigram.ai.llm.admin.pages.overview:LlmOverviewPage",
                category=PageCategory.AI,
                icon="sparkles",
                description="Overview of LLM providers, active model, and client status",
                order=10,
            ),
            ManagementPageDefinition(
                name="llm_usage",
                title="LLM Usage",
                contributor="ai-llm",
                route_path="/ai/llm/usage",
                handler="lexigram.ai.llm.admin.pages.usage:LlmUsagePage",
                category=PageCategory.AI,
                icon="bar-chart-2",
                description="Token usage statistics and cost estimates",
                order=20,
            ),
            ManagementPageDefinition(
                name="llm_providers",
                title="LLM Providers",
                contributor="ai-llm",
                route_path="/ai/llm/providers",
                handler="lexigram.ai.llm.admin.pages.providers:LlmProvidersPage",
                category=PageCategory.AI,
                icon="server",
                description="Configured LLM provider status and health",
                order=30,
            ),
        ]

    async def _render_error_rate(self) -> WidgetViewModel:
        if self._container is None:
            return WidgetViewModel(body="<p>Contributor not booted.</p>")

        logger = await self._container.resolve(InferenceLoggerProtocol)
        logs = await logger.get_recent(limit=500)

        if not logs:
            body = el(
                "div",
                el("p", "No inference data yet.", class_="text-gray-500 text-sm"),
                class_="space-y-2",
            )
            return WidgetViewModel(body=str(el("div", body)))

        total = len(logs)
        errors = sum(1 for log in logs if not log.succeeded)
        rate = (errors / total * 100) if total > 0 else 0.0

        color = (
            "text-green-600"
            if rate < 5
            else "text-yellow-600"
            if rate < 15
            else "text-red-600"
        )

        body = el(
            "div",
            el(
                "div",
                el("span", f"{rate:.1f}%", class_=f"text-3xl font-bold {color}"),
                el("span", " error rate", class_="text-gray-500 text-sm ml-1"),
                class_="mb-2",
            ),
            el(
                "div",
                el("span", f"{errors}", class_="font-semibold"),
                el(
                    "span",
                    f" errors / {total} requests",
                    class_="text-gray-500 text-sm ml-1",
                ),
                class_="text-sm",
            ),
            class_="space-y-1",
        )
        return WidgetViewModel(body=str(el("div", body, class_="p-2")))

    async def _render_provider_status(self) -> WidgetViewModel:
        if self._container is None:
            return WidgetViewModel(body="<p>Contributor not booted.</p>")

        router = await self._container.resolve(LLMRouterProtocol)

        rows = []
        for provider_cfg in router._config.providers:
            client = router._clients.get(provider_cfg.name)
            if client is None or not provider_cfg.enabled:
                dot = el("span", "●", class_="text-gray-400 mr-1.5", aria_hidden="true")
                rows.append(
                    el(
                        "tr",
                        el(
                            "td",
                            el("span", provider_cfg.name, class_="font-medium"),
                            class_="py-1.5 pr-3",
                        ),
                        el(
                            "td",
                            provider_cfg.model,
                            class_="py-1.5 pr-3 text-gray-500 text-sm",
                        ),
                        el(
                            "td",
                            dot,
                            el(
                                "span", "not configured", class_="text-gray-400 text-sm"
                            ),
                            class_="py-1.5 pr-3",
                        ),
                        el("td", "—", class_="py-1.5 text-gray-400 text-sm"),
                    )
                )
                continue

            try:
                result = await client.health_check(timeout=5.0)
            except Exception:
                rows.append(
                    el(
                        "tr",
                        el(
                            "td",
                            el("span", provider_cfg.name, class_="font-medium"),
                            class_="py-1.5 pr-3",
                        ),
                        el(
                            "td",
                            provider_cfg.model,
                            class_="py-1.5 pr-3 text-gray-500 text-sm",
                        ),
                        el(
                            "td",
                            el(
                                "span",
                                "●",
                                class_="text-red-500 mr-1.5",
                                aria_hidden="true",
                            ),
                            el("span", "error", class_="text-red-600 text-sm"),
                            class_="py-1.5 pr-3",
                        ),
                        el("td", "—", class_="py-1.5 text-gray-400 text-sm"),
                    )
                )
                continue

            if result.status == HealthStatus.HEALTHY:
                dot_class = "text-green-500"
                status_label = "healthy"
                status_class = "text-green-600"
            elif result.status == HealthStatus.DEGRADED:
                dot_class = "text-yellow-500"
                status_label = "degraded"
                status_class = "text-yellow-600"
            else:
                dot_class = "text-red-500"
                status_label = result.status.value
                status_class = "text-red-600"

            latency = f"{result.duration_ms:.0f}ms" if result.duration_ms > 0 else "—"

            rows.append(
                el(
                    "tr",
                    el(
                        "td",
                        el("span", provider_cfg.name, class_="font-medium"),
                        class_="py-1.5 pr-3",
                    ),
                    el(
                        "td",
                        provider_cfg.model,
                        class_="py-1.5 pr-3 text-gray-500 text-sm",
                    ),
                    el(
                        "td",
                        el(
                            "span",
                            "●",
                            class_=f"{dot_class} mr-1.5",
                            aria_hidden="true",
                        ),
                        el("span", status_label, class_=f"{status_class} text-sm"),
                        class_="py-1.5 pr-3",
                    ),
                    el("td", latency, class_="py-1.5 text-gray-500 text-sm"),
                )
            )

        if not rows:
            body = el("p", "No providers configured.", class_="text-gray-500 text-sm")
            return WidgetViewModel(body=str(body))

        table = el(
            "table",
            el(
                "thead",
                el(
                    "tr",
                    el(
                        "th",
                        "Provider",
                        class_="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Model",
                        class_="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Status",
                        class_="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Latency",
                        class_="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1",
                        scope_="col",
                    ),
                ),
            ),
            el("tbody", *rows, class_="divide-y divide-gray-100"),
            class_="w-full",
        )

        return WidgetViewModel(body=str(el("div", table, class_="p-1")))

    async def _render_token_usage(self) -> WidgetViewModel:
        if self._container is None:
            return WidgetViewModel(body="<p>Contributor not booted.</p>")

        logger = await self._container.resolve(InferenceLoggerProtocol)
        logs = await logger.get_recent(limit=1000)

        by_provider: dict[str, dict[str, int]] = {}
        for log in logs:
            if log.result is None:
                continue
            provider = log.result.provider
            if provider not in by_provider:
                by_provider[provider] = {"prompt": 0, "completion": 0, "count": 0}
            by_provider[provider]["prompt"] += log.result.prompt_tokens
            by_provider[provider]["completion"] += log.result.completion_tokens
            by_provider[provider]["count"] += 1

        if not by_provider:
            body = el("p", "No inference data yet.", class_="text-gray-500 text-sm")
            return WidgetViewModel(body=str(body))

        all_total = sum(v["prompt"] + v["completion"] for v in by_provider.values())

        rows = []
        for provider, counts in sorted(by_provider.items()):
            total = counts["prompt"] + counts["completion"]
            pct = f"({total / all_total * 100:.0f}%)" if all_total else ""
            rows.append(
                el(
                    "tr",
                    el("td", provider, class_="py-1.5 pr-3 font-medium"),
                    el(
                        "td",
                        f"{counts['prompt']:,}",
                        class_="py-1.5 pr-3 text-right text-sm tabular-nums",
                    ),
                    el(
                        "td",
                        f"{counts['completion']:,}",
                        class_="py-1.5 pr-3 text-right text-sm tabular-nums",
                    ),
                    el(
                        "td",
                        f"{total:,}",
                        class_="py-1.5 pr-3 text-right text-sm tabular-nums font-semibold",
                    ),
                    el("td", pct, class_="py-1.5 text-gray-400 text-sm"),
                )
            )

        table = el(
            "table",
            el(
                "thead",
                el(
                    "tr",
                    el(
                        "th",
                        "Provider",
                        class_="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Prompt",
                        class_="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Completion",
                        class_="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Total",
                        class_="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "%",
                        class_="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider pb-1",
                        scope_="col",
                    ),
                ),
            ),
            el("tbody", *rows, class_="divide-y divide-gray-100"),
            class_="w-full",
        )

        return WidgetViewModel(body=str(el("div", table, class_="p-1")))

    async def render_health_check(
        self,
        check_name: str,
    ) -> Result[HealthCheckPayload, AdminError]:
        """Aggregate health across all enabled LLM providers.

        Delegates to ``LLMRouterProtocol.health_probe()`` — the same
        ``client.health_check()`` calls the provider-status widget makes,
        aggregated at the protocol boundary (no private router attrs).

        Args:
            check_name: Name of the health check requested.

        Returns:
            Ok(HealthCheckPayload) — HEALTHY when at least one enabled
            provider passes its health probe, UNHEALTHY when none does.
            Err(HealthCheckNotFoundError) for unknown check names or when
            the contributor was never booted.
        """
        if check_name != "provider" or self._container is None:
            not_found: Result[HealthCheckPayload, AdminError] = cast(
                "Result[HealthCheckPayload, AdminError]",
                Err(HealthCheckNotFoundError(self.name, check_name)),
            )
            return not_found

        router = await self._container.resolve(LLMRouterProtocol)
        result = await router.health_probe()
        if result.is_ok():
            return Ok(
                HealthCheckPayload(
                    status=HealthStatus.HEALTHY,
                    component="LLM Provider",
                )
            )
        return Ok(
            HealthCheckPayload(
                status=HealthStatus.UNHEALTHY,
                component="LLM Provider",
                detail="no healthy provider",
            )
        )

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        resolver: ContainerResolverProtocol | None = None,
    ) -> Result[WidgetViewModel, AdminError]:
        widget_names = {w.name for w in _WIDGETS}
        if widget_name not in widget_names:
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError(self.name, widget_name)),
            )

        if widget_name == "token_usage":
            vm = await self._render_token_usage()
            return Ok(vm)

        if widget_name == "provider_status":
            vm = await self._render_provider_status()
            return Ok(vm)

        if widget_name == "error_rate":
            vm = await self._render_error_rate()
            return Ok(vm)

        return Ok(
            WidgetViewModel(body=f"<p>Widget '{widget_name}' not yet implemented.</p>")
        )


__all__ = ["LlmAdminContributor"]
