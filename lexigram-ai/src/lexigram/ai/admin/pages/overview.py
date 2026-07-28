from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.ai.config import AIConfig
from lexigram.contracts.ai.providers import ProviderRegistryProtocol
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class AIPipelineOverviewPage:
    """Management page for /admin/ai/pipeline — AI subsystem overview."""

    def __init__(
        self,
        config: AIConfig | None = None,
        registry: ProviderRegistryProtocol | None = None,
    ) -> None:
        self._config = config
        self._registry = registry

    async def handle(self, request: Any) -> HTMLResponse:
        ai_enabled: bool = False
        provider_count: str | int = "N/A"
        model_count: str | int = "N/A"
        subsystems: list[dict[str, str]] = []

        if self._config is not None:
            ai_enabled = self._config.enabled
            config_fields = {
                "LLM": self._config.llm,
                "Vector": self._config.vector,
                "RAG": self._config.rag,
                "Governance": self._config.governance,
                "Observability": self._config.observability,
            }
            for name, cfg in config_fields.items():
                enabled = bool(cfg and getattr(cfg, "enabled", True))
                subsystems.append({"name": name, "enabled": str(enabled)})

        if self._registry is not None:
            try:
                providers = self._registry.list_providers()
                provider_count = len(providers)
            except Exception:
                provider_count = "N/A"
            try:
                models = self._registry.list_models()
                model_count = len(models)
            except Exception:
                model_count = "N/A"

        status_value = "Active" if ai_enabled else "Inactive"
        status_icon = "activity" if ai_enabled else "power"

        subsystem_rows = []
        for s in subsystems:
            enabled_dot = el(
                "span",
                "●",
                class_="text-green-500 mr-1.5"
                if s["enabled"] == "True"
                else "text-gray-400 mr-1.5",
                aria_hidden="true",
            )
            subsystem_rows.append(
                el(
                    "tr",
                    el("td", s["name"], class_="py-1.5 pr-3 font-medium"),
                    el(
                        "td",
                        enabled_dot,
                        el(
                            "span",
                            "Enabled" if s["enabled"] == "True" else "Disabled",
                            class_="text-sm",
                        ),
                        class_="py-1.5",
                    ),
                    class_="divide-x divide-[var(--border)]",
                )
            )

        subsystem_table = el(
            "table",
            el(
                "thead",
                el(
                    "tr",
                    el(
                        "th",
                        "Subsystem",
                        class_="text-left text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Status",
                        class_="text-left text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider pb-1",
                        scope_="col",
                    ),
                ),
            ),
            el("tbody", *subsystem_rows, class_="divide-y divide-[var(--border)]"),
            class_="w-full",
        )

        config_details = []
        if self._config is not None:
            governance_enabled = (
                bool(getattr(self._config.governance, "enabled", False))
                if self._config.governance
                else False
            )
            config_details = [
                ("AI Enabled", str(ai_enabled)),
                ("Providers Registered", str(provider_count)),
                ("Models Available", str(model_count)),
                ("Governance", str(governance_enabled)),
            ]

        config_html = (
            el(
                "dl",
                *[
                    el(
                        "div",
                        el(
                            "dt",
                            label,
                            class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                        ),
                        el("dd", value, class_="text-sm text-[var(--foreground)] pb-3"),
                    )
                    for label, value in config_details
                ],
                class_="divide-y divide-[var(--border)]",
            )
            if config_details
            else el(
                "p",
                "No configuration available.",
                class_="text-sm text-[var(--muted-foreground)]",
            )
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "AI Pipeline",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "AI subsystem pipeline overview, provider registry, and configuration status.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Pipeline Status", value=status_value, icon=status_icon
                    ),
                    StatCard(
                        label="Providers", value=str(provider_count), icon="server"
                    ),
                    StatCard(label="Models", value=str(model_count), icon="cpu"),
                    cols={"default": 1, "lg": 3},
                    gap=4,
                ),
                Card(
                    title="AI Subsystems",
                    content=render_to_string(subsystem_table)
                    if subsystem_rows
                    else render_to_string(
                        el(
                            "p",
                            "No AI subsystems configured.",
                            class_="text-sm text-[var(--muted-foreground)] py-4",
                        )
                    ),
                ),
                Card(
                    title="Configuration Summary",
                    content=render_to_string(config_html),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
