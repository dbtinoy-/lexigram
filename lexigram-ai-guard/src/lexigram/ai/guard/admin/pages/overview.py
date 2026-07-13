from __future__ import annotations

from typing import Any

from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import EmptyContent, Stat, StatContent
from lexigram.logging import get_logger

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

    async def handle(self, request: Any) -> PageContent:
        if self._config is None and self._pipeline is None:
            return PageContent(
                title="Moderation",
                body=EmptyContent(
                    title="Moderation Unavailable",
                    message="The guard pipeline could not be resolved.",
                    icon="shield",
                ),
            )

        enabled: bool = False
        input_count: int = 0
        output_count: int = 0

        if self._config is not None:
            enabled = self._config.enabled

        if self._pipeline is not None:
            raw_inputs = self._pipeline._input_guards
            raw_outputs = self._pipeline._output_guards
            input_count = len(raw_inputs)
            output_count = len(raw_outputs)

        status_value = "Active" if enabled else "Disabled"
        status_icon = "shield-check" if enabled else "shield-off"

        return PageContent(
            title="Moderation",
            body=StatContent(
                stats=(
                    Stat(label="Status", value=status_value, icon=status_icon),
                    Stat(
                        label="Input Guards",
                        value=str(input_count),
                        icon="log-in",
                    ),
                    Stat(
                        label="Output Guards",
                        value=str(output_count),
                        icon="log-out",
                    ),
                )
            ),
        )
