from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.ai.llm import LLMClientProtocol
from lexigram.contracts.ai.providers import ProviderRegistryProtocol
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class LlmOverviewPage:
    """Dashboard overview for /admin/ai/llm."""

    def __init__(
        self,
        registry: ProviderRegistryProtocol | None = None,
        client: LLMClientProtocol | None = None,
    ) -> None:
        self._registry = registry
        self._client = client

    async def handle(self, request: Any) -> HTMLResponse:
        provider_count: str | int = "N/A"
        active_model: str = "N/A"
        client_status: str = "N/A"

        if self._registry is not None:
            try:
                providers = self._registry.list_providers()
                provider_count = len(providers)
            except Exception:
                provider_count = "N/A"

            try:
                models = self._registry.list_models()
                active_model = models[0].display_name if models else "None"
            except Exception:
                active_model = "N/A"

        if self._client is not None:
            try:
                result = await self._client.health_check()
                client_status = f"{result.duration_ms:.0f}ms"
            except Exception:
                client_status = "error"

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "AI / LLM",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "LLM provider overview, active models, and client status.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Providers",
                        value=str(provider_count),
                        icon="server",
                    ),
                    StatCard(
                        label="Active Model",
                        value=str(active_model),
                        icon="cpu",
                    ),
                    StatCard(
                        label="Client Latency",
                        value=str(client_status),
                        icon="activity",
                    ),
                    cols={"default": 1, "lg": 3},
                    gap=4,
                ),
                Card(
                    title="Registry Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Providers Registered",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(provider_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Active Model",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(active_model),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Client Latency",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(client_status),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        ),
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
