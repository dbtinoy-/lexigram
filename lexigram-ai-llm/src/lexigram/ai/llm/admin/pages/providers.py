from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.ai.providers import ProviderRegistryProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.logging import get_logger
from lexigram.ui import (
    Badge,
    Divider,
    EmptyState,
    el,
    render_to_string,
)
from lexigram.ui.atoms.badge import BadgeVariant

logger = get_logger(__name__)


class LlmProvidersPage:
    """Provider status table for /admin/ai/llm/providers."""

    def __init__(
        self,
        registry: ProviderRegistryProtocol | None = None,
    ) -> None:
        self._registry = registry

    async def handle(self, request: Any) -> HTMLResponse:
        if self._registry is None:
            html = render_to_string(
                EmptyState(
                    title="Provider Registry Unavailable",
                    message="No provider registry is configured. Provider status cannot be displayed.",
                    icon="server",
                ),
            )
            return HTMLResponse(html)

        provider_names: list[str] = []
        try:
            provider_names = self._registry.list_providers()
        except Exception:
            provider_names = []

        if not provider_names:
            html = render_to_string(
                EmptyState(
                    title="No Providers",
                    message="No LLM providers are configured.",
                    icon="server",
                ),
            )
            return HTMLResponse(html)

        all_models: list[Any] = []
        try:
            all_models = self._registry.list_models()
        except Exception:
            all_models = []

        model_map: dict[str, str] = {}
        for m in all_models:
            if m.provider not in model_map:
                model_map[m.provider] = m.model_id

        provider_data: list[tuple[str, str, str, BadgeVariant, str]] = []
        for name in provider_names:
            model_name = model_map.get(name, "\u2014")
            status_label = "unknown"
            status_variant: BadgeVariant = "warning"
            latency = "\u2014"

            try:
                client = await self._registry.get_client(name)
            except Exception:
                client = None

            if client is not None:
                try:
                    result = await client.health_check(timeout=5.0)
                    if result.status == HealthStatus.HEALTHY:
                        status_label = "healthy"
                        status_variant = "success"
                    elif result.status == HealthStatus.DEGRADED:
                        status_label = "degraded"
                        status_variant = "warning"
                    else:
                        status_label = result.status.value
                        status_variant = "danger"
                    latency = (
                        f"{result.duration_ms:.0f}ms"
                        if result.duration_ms > 0
                        else "\u2014"
                    )
                except Exception:
                    status_label = "error"
                    status_variant = "danger"
                    latency = "\u2014"
            else:
                status_label = "not configured"
                status_variant = "warning"

            provider_data.append(
                (name, model_name, status_label, status_variant, latency)
            )

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        name,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        model_name,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        Badge(status_label, variant=status_variant),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        latency,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for name, model_name, status_label, status_variant, latency in provider_data
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "LLM Providers",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Configured LLM providers, their models, and health status.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                el(
                    "div",
                    el(
                        "table",
                        el(
                            "thead",
                            el(
                                "tr",
                                el(
                                    "th",
                                    "Provider",
                                    style="width:20%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Model",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Latency",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el(
                            "tbody",
                            rows,
                            class_="divide-y divide-[var(--border)]",
                        ),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
