from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.ai.llm import TokenCounterProtocol
from lexigram.contracts.ai.routing import InferenceLoggerProtocol
from lexigram.logging import get_logger
from lexigram.ui import (
    Card,
    Divider,
    EmptyState,
    Grid,
    StatCard,
    el,
    render_to_string,
)

logger = get_logger(__name__)


class LlmUsagePage:
    """Usage statistics for /admin/ai/llm/usage."""

    def __init__(
        self,
        counter: TokenCounterProtocol | None = None,
        logger: InferenceLoggerProtocol | None = None,
    ) -> None:
        self._counter = counter
        self._logger = logger

    async def handle(self, request: Any) -> HTMLResponse:
        if self._logger is None:
            html = render_to_string(
                EmptyState(
                    title="Usage Data Unavailable",
                    message="No inference logger is configured. Usage statistics cannot be displayed.",
                    icon="bar-chart-2",
                ),
            )
            return HTMLResponse(html)

        logs: list[Any] = []
        try:
            logs = await self._logger.get_recent(limit=500)
        except Exception:
            logs = []

        if not logs:
            html = render_to_string(
                EmptyState(
                    title="No Usage Data",
                    message="No inference data has been recorded yet.",
                    icon="inbox",
                ),
            )
            return HTMLResponse(html)

        total_prompt = 0
        total_completion = 0
        total_cost = 0.0
        success_count = 0
        for log in logs:
            if not log.succeeded or log.result is None:
                continue
            result = log.result
            total_prompt += getattr(result, "prompt_tokens", 0)
            total_completion += getattr(result, "completion_tokens", 0)
            total_cost += getattr(result, "cost", 0.0)
            success_count += 1

        total_tokens = total_prompt + total_completion

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Usage",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Token consumption and cost tracking across LLM providers.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Total Tokens",
                        value=f"{total_tokens:,}",
                        icon="align-left",
                    ),
                    StatCard(
                        label="Prompt Tokens",
                        value=f"{total_prompt:,}",
                        icon="corner-up-left",
                    ),
                    StatCard(
                        label="Completion Tokens",
                        value=f"{total_completion:,}",
                        icon="corner-down-right",
                    ),
                    StatCard(
                        label="Estimated Cost",
                        value=f"${total_cost:.4f}",
                        icon="dollar-sign",
                    ),
                    cols={"default": 1, "lg": 4},
                    gap=4,
                ),
                Card(
                    title="Summary",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Successful Requests",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(success_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Total Tokens",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                f"{total_tokens:,}",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Estimated Cost",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                f"${total_cost:.4f}",
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
