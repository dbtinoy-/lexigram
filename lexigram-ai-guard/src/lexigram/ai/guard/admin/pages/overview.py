from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class ModerationOverviewPage:
    """Management page for /admin/ai/moderation — guard pipeline status."""

    def __init__(
        self,
        pipeline: GuardPipeline | None = None,
        config: GuardConfig | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._config = config

    async def handle(self, request: Any) -> HTMLResponse:
        enabled: bool = False
        input_count: int = 0
        output_count: int = 0
        input_guards: list[dict[str, str]] = []
        output_guards: list[dict[str, str]] = []

        if self._config is not None:
            enabled = self._config.enabled

        if self._pipeline is not None:
            raw_inputs = self._pipeline._input_guards
            raw_outputs = self._pipeline._output_guards
            input_count = len(raw_inputs)
            output_count = len(raw_outputs)
            for inp_guard in raw_inputs:
                input_guards.append(
                    {
                        "name": inp_guard.name,
                        "action": getattr(inp_guard, "_action", "n/a"),
                    }
                )
            for out_guard in raw_outputs:
                output_guards.append(
                    {
                        "name": out_guard.name,
                        "action": getattr(out_guard, "_action", "n/a"),
                    }
                )

        status_value = "Active" if enabled else "Disabled"
        status_icon = "shield-check" if enabled else "shield-off"

        guard_rows: list[Any] = []
        for inp in input_guards:
            guard_rows.append(
                el(
                    "tr",
                    el("td", inp["name"], class_="py-1.5 pr-3 font-medium text-sm"),
                    el(
                        "td",
                        "input",
                        class_="py-1.5 pr-3 text-sm text-[var(--muted-foreground)]",
                    ),
                    el("td", inp["action"], class_="py-1.5 text-sm"),
                    class_="divide-x divide-[var(--border)]",
                )
            )
        for out in output_guards:
            guard_rows.append(
                el(
                    "tr",
                    el("td", out["name"], class_="py-1.5 pr-3 font-medium text-sm"),
                    el(
                        "td",
                        "output",
                        class_="py-1.5 pr-3 text-sm text-[var(--muted-foreground)]",
                    ),
                    el("td", out["action"], class_="py-1.5 text-sm"),
                    class_="divide-x divide-[var(--border)]",
                )
            )

        guard_table = el(
            "table",
            el(
                "thead",
                el(
                    "tr",
                    el(
                        "th",
                        "Name",
                        class_="text-left text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Type",
                        class_="text-left text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider pb-1 pr-3",
                        scope_="col",
                    ),
                    el(
                        "th",
                        "Action",
                        class_="text-left text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider pb-1",
                        scope_="col",
                    ),
                ),
            ),
            el("tbody", *guard_rows, class_="divide-y divide-[var(--border)]"),
            class_="w-full",
        )

        config_details = []
        if self._config is not None:
            config_details = [
                ("Injection Detection", str(self._config.injection_detection)),
                ("PII Detection", str(self._config.pii_detection)),
                ("PII Redaction Output", str(self._config.pii_redaction_output)),
                (
                    "Max Input Chars",
                    str(self._config.max_input_chars)
                    if self._config.max_input_chars > 0
                    else "Unlimited",
                ),
                (
                    "Max Output Chars",
                    str(self._config.max_output_chars)
                    if self._config.max_output_chars > 0
                    else "Unlimited",
                ),
                ("LLM Guards", str(self._config.enable_llm_guards)),
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
                    "Moderation",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Content safety guard pipeline overview and status.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Status", value=status_value, icon=status_icon),
                    StatCard(
                        label="Input Guards", value=str(input_count), icon="log-in"
                    ),
                    StatCard(
                        label="Output Guards", value=str(output_count), icon="log-out"
                    ),
                    cols={"default": 1, "lg": 3},
                    gap=4,
                ),
                Card(
                    title="Active Guards",
                    content=render_to_string(guard_table)
                    if guard_rows
                    else render_to_string(
                        el(
                            "p",
                            "No guards configured.",
                            class_="text-sm text-[var(--muted-foreground)] py-4",
                        )
                    ),
                ),
                Card(
                    title="Configuration",
                    content=render_to_string(config_html),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
