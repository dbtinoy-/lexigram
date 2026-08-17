"""Base protocol and interfaces for pipeline stages."""

from __future__ import annotations

from typing import Protocol

from lexigram.ai.rag.pipeline.types import PipelineContext


class PipelineStageProtocol(Protocol):
    """Protocol for pipeline stages.

    Each stage processes the context and returns an updated context.
    Stages should be independent and idempotent where possible.
    """

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Process the pipeline context.

        Args:
            context: The current pipeline context

        Returns:
            Updated pipeline context

        Raises:
            Exception: If stage processing fails and error strategy is FAIL_FAST
        """
        ...

    @property
    def name(self) -> str:
        """Get the stage name.

        Returns:
            Name of the stage
        """
        ...
