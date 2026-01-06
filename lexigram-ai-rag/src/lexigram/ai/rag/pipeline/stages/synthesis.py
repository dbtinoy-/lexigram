"""Synthesis stage for response generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.ai.rag.synthesis.synthesizers.base import ResponseSynthesizerProtocol

if TYPE_CHECKING:
    from lexigram.contracts.ai import LLMClientProtocol

from lexigram.ai.rag.config import SynthesisConfig
from lexigram.ai.rag.pipeline.types import PipelineContext
from lexigram.ai.rag.synthesis import (
    AbstractiveSynthesizer,
    DirectSynthesizer,
    ExtractiveSynthesizer,
    HybridSynthesizer,
    ResponseSynthesizerProtocol,
    SynthesisStrategy,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class SynthesisStage:
    """Pipeline stage for response synthesis.

    This stage generates a response from the retrieved context chunks
    using the configured synthesis strategy.
    """

    def __init__(
        self,
        config: SynthesisConfig,
        llm_client: LLMClientProtocol | None = None,
    ):
        """Initialize the synthesis stage.

        Args:
            config: Synthesis configuration
            llm_client: Optional LLM client for abstractive/hybrid synthesis
        """
        self.config = config
        self.llm_client = llm_client
        self._synthesizer: ResponseSynthesizerProtocol | None = None

    @property
    def name(self) -> str:
        """Get stage name."""
        return "synthesis"

    async def process(self, context: PipelineContext) -> PipelineContext:
        """Process the synthesis stage.

        Args:
            context: Pipeline context with retrieved chunks

        Returns:
            Updated context with synthesis result
        """
        if not self.config.enabled:
            logger.info("Synthesis stage disabled, skipping")
            return context

        # Check if we have chunks to synthesize from
        chunks_to_use = context.optimized_chunks or context.retrieved_chunks
        if not chunks_to_use:
            logger.warning("No chunks available for synthesis")
            context.add_warning("No chunks available for synthesis")
            return context

        # Get or create synthesizer
        synthesizer = self._get_synthesizer()

        try:
            # Synthesize response
            logger.info(
                "Synthesizing response",
                extra={
                    "request_id": context.request_id,
                    "strategy": self.config.strategy.value,
                    "num_chunks": len(chunks_to_use),
                },
            )

            result = await synthesizer._synthesize_internal(
                query=context.query,
                context_chunks=chunks_to_use,
            )

            # Store result in context
            context.synthesis_result = result

            logger.info(
                "Synthesis completed",
                extra={
                    "request_id": context.request_id,
                    "response_length": len(result.response),
                    "chunks_used": result.num_chunks_used,
                    "sources": len(result.sources),
                },
            )

        except Exception as e:
            logger.exception(
                "Synthesis failed",
                extra={
                    "request_id": context.request_id,
                    "strategy": self.config.strategy.value,
                    "error": str(e),
                },
            )

            # Try fallback if configured
            if (
                self.config.error_strategy == "fallback"
                and self.config.strategy != self.config.fallback_strategy
            ):
                logger.info(
                    "Attempting fallback synthesis strategy",
                    extra={
                        "request_id": context.request_id,
                        "fallback_strategy": self.config.fallback_strategy,
                    },
                )

                try:
                    fallback_synthesizer = self._get_fallback_synthesizer()
                    result = await fallback_synthesizer._synthesize_internal(
                        query=context.query,
                        context_chunks=chunks_to_use,
                    )
                    context.synthesis_result = result
                    context.add_warning(
                        f"Used fallback synthesis strategy: {self.config.fallback_strategy}",
                    )
                except Exception as fallback_error:
                    logger.exception(
                        "Fallback synthesis also failed",
                        extra={
                            "request_id": context.request_id,
                            "error": str(fallback_error),
                        },
                    )
                    raise e from fallback_error  # Raise original error with fallback cause
            else:
                raise

        return context

    def _get_synthesizer(self) -> ResponseSynthesizerProtocol:
        """Get or create the configured synthesizer.

        Returns:
            Response synthesizer instance
        """
        if self._synthesizer is not None:
            return cast("ResponseSynthesizerProtocol", self._synthesizer)

        from lexigram.ai.rag.pipeline.stages.synthesis_registry import (
            SynthesisStrategyRegistry,
        )

        strategy = self.config.strategy
        registry = SynthesisStrategyRegistry.with_defaults()
        self._synthesizer = registry.create_synthesizer(
            strategy,
            self.config,
            self.llm_client,
        )

        return cast("ResponseSynthesizerProtocol", self._synthesizer)

    def _get_fallback_synthesizer(self) -> ResponseSynthesizerProtocol:
        """Get the fallback synthesizer.

        Returns:
            Fallback synthesizer instance
        """
        strategy = self.config.fallback_strategy

        if strategy == SynthesisStrategy.DIRECT:
            return DirectSynthesizer(
                separator="\n\n",
                max_chunks=None,
                include_sources=self.config.include_citations,
            )

        if strategy == SynthesisStrategy.EXTRACTIVE:
            return ExtractiveSynthesizer(
                max_sentences=10,
                min_sentence_length=20,
            )

        if strategy == SynthesisStrategy.ABSTRACTIVE:
            if self.llm_client is None:
                # Fall back to extractive if no LLM
                return ExtractiveSynthesizer(
                    max_sentences=10,
                    min_sentence_length=20,
                )
            return AbstractiveSynthesizer(
                llm_client=self.llm_client,
                max_context_chunks=5,
                include_citations=self.config.include_citations,
            )

        if strategy == SynthesisStrategy.HYBRID:
            if self.llm_client is None:
                # Fall back to extractive if no LLM
                return ExtractiveSynthesizer(
                    max_sentences=10,
                    min_sentence_length=20,
                )
            return HybridSynthesizer(
                llm_client=self.llm_client,
                extraction_ratio=0.5,
                max_extractive_sentences=8,
            )

        msg = f"Unknown fallback synthesis strategy: {strategy}"
        raise ValueError(msg)
