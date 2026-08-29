"""Synthesis strategy registry for RAG pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from lexigram.ai.rag.synthesis.types import SynthesisStrategy
    from lexigram.contracts.ai import LLMClientProtocol


class SynthesisStrategyHandler(Protocol):
    """Protocol for synthesis strategy handlers."""

    def can_handle(self, strategy: SynthesisStrategy) -> bool:
        """Check if this handler can handle the strategy."""
        ...

    def create_synthesizer(
        self, config: Any, llm_client: LLMClientProtocol | None
    ) -> Any:
        """Create a synthesizer instance."""
        ...


class DirectSynthesisStrategyHandler:
    """Handler for DIRECT synthesis strategy."""

    def can_handle(self, strategy: SynthesisStrategy) -> bool:
        from lexigram.ai.rag.pipeline.stages.synthesis import SynthesisStrategy

        return strategy == SynthesisStrategy.DIRECT

    def create_synthesizer(
        self, config: Any, llm_client: LLMClientProtocol | None
    ) -> Any:
        from lexigram.ai.rag.pipeline.stages.synthesis import DirectSynthesizer

        return DirectSynthesizer(
            separator="\n\n",
            max_chunks=None,
            include_sources=config.include_citations,
        )


class ExtractiveSynthesisStrategyHandler:
    """Handler for EXTRACTIVE synthesis strategy."""

    def can_handle(self, strategy: SynthesisStrategy) -> bool:
        from lexigram.ai.rag.pipeline.stages.synthesis import SynthesisStrategy

        return strategy == SynthesisStrategy.EXTRACTIVE

    def create_synthesizer(
        self, config: Any, llm_client: LLMClientProtocol | None
    ) -> Any:
        from lexigram.ai.rag.pipeline.stages.synthesis import ExtractiveSynthesizer

        return ExtractiveSynthesizer(
            max_sentences=10,
            min_sentence_length=20,
        )


class AbstractiveSynthesisStrategyHandler:
    """Handler for ABSTRACTIVE synthesis strategy."""

    def can_handle(self, strategy: SynthesisStrategy) -> bool:
        from lexigram.ai.rag.pipeline.stages.synthesis import SynthesisStrategy

        return strategy == SynthesisStrategy.ABSTRACTIVE

    def create_synthesizer(
        self, config: Any, llm_client: LLMClientProtocol | None
    ) -> Any:
        from lexigram.ai.rag.pipeline.stages.synthesis import (
            AbstractiveSynthesizer,
            ExtractiveSynthesizer,
        )
        from lexigram.logging import get_logger

        logger = get_logger(__name__)
        if llm_client is None:
            logger.warning(
                "LLM client not provided for abstractive synthesis, "
                "falling back to extractive",
            )
            return ExtractiveSynthesizer(
                max_sentences=10,
                min_sentence_length=20,
            )
        return AbstractiveSynthesizer(
            llm_client=llm_client,
            max_context_chunks=5,
            include_citations=config.include_citations,
        )


class HybridSynthesisStrategyHandler:
    """Handler for HYBRID synthesis strategy."""

    def can_handle(self, strategy: SynthesisStrategy) -> bool:
        from lexigram.ai.rag.pipeline.stages.synthesis import SynthesisStrategy

        return strategy == SynthesisStrategy.HYBRID

    def create_synthesizer(
        self, config: Any, llm_client: LLMClientProtocol | None
    ) -> Any:
        from lexigram.ai.rag.pipeline.stages.synthesis import (
            ExtractiveSynthesizer,
            HybridSynthesizer,
        )
        from lexigram.logging import get_logger

        logger = get_logger(__name__)
        if llm_client is None:
            logger.warning(
                "LLM client not provided for hybrid synthesis, "
                "falling back to extractive",
            )
            return ExtractiveSynthesizer(
                max_sentences=10,
                min_sentence_length=20,
            )
        return HybridSynthesizer(
            llm_client=llm_client,
            max_extractive_sentences=5,
        )


class SynthesisStrategyRegistry:
    """Central registry for synthesis strategy handlers."""

    def __init__(self) -> None:
        self._handlers: list[SynthesisStrategyHandler] = []

    @classmethod
    def _default_entries(cls) -> dict[str, object]:
        """Declare the built-in strategy handlers."""
        return {
            "direct": DirectSynthesisStrategyHandler(),
            "extractive": ExtractiveSynthesisStrategyHandler(),
            "abstractive": AbstractiveSynthesisStrategyHandler(),
            "hybrid": HybridSynthesisStrategyHandler(),
        }

    @classmethod
    def with_defaults(cls) -> SynthesisStrategyRegistry:
        """Create a registry pre-populated with all built-in strategy handlers."""
        registry = cls()
        registry._handlers = list(cls._default_entries().values())
        return registry

    def register(self, handler: SynthesisStrategyHandler) -> None:
        """Register a new strategy handler."""
        self._handlers.insert(0, handler)

    def create_synthesizer(
        self,
        strategy: SynthesisStrategy,
        config: Any,
        llm_client: LLMClientProtocol | None,
    ) -> Any:
        """Create a synthesizer for the given strategy."""
        for handler in self._handlers:
            if handler.can_handle(strategy):
                return handler.create_synthesizer(config, llm_client)
        raise ValueError(f"Unknown synthesis strategy: {strategy}")
