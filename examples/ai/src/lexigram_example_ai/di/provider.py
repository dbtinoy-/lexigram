"""AIProvider — DI composition root for the AI pipeline example.

Wires together:
- A stub :class:`~lexigram.contracts.ai.llm.LLMClientProtocol` (replace with
  a real OpenAI / Anthropic adapter in production)
- A stub :class:`~lexigram.contracts.ai.llm.EmbeddingClientProtocol`
- A stub :class:`~lexigram.contracts.ai.llm.TokenCounterProtocol`
- An in-memory :class:`~lexigram.contracts.ai.vector.DocumentVectorStoreProtocol`
- :class:`~lexigram_example_ai.pipelines.chat_pipeline.ChatPipeline`
- :class:`~lexigram_example_ai.pipelines.rag_pipeline.RAGPipeline`
- :class:`~lexigram_example_ai.tools.summarise_tool.SummariseTool`

Set the ``AI_LLM_DRIVER`` environment variable to swap the LLM backend
without touching application code — the provider reads
:class:`~lexigram_example_ai.config.AIConfig` and selects the right binding.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.llm import ChatMessage, Role
from lexigram.contracts.core import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_ai.config import AIConfig
from lexigram_example_ai.pipelines.chat_pipeline import ChatPipeline
from lexigram_example_ai.pipelines.rag_pipeline import RAGPipeline
from lexigram_example_ai.tools.summarise_tool import SummariseTool

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.ai.exceptions import LLMError

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Development-only stubs
#
# Replace these with real provider implementations (e.g. from
# lexigram-ai-llm) by overriding the AIProvider.register bindings.
# ---------------------------------------------------------------------------


class _StubCompletion:
    """Minimal completion response for the stub LLM client."""

    def __init__(self, content: str, model: str = "stub") -> None:
        self.content = content
        self.model = model


class _StubLLMClient:
    """No-op LLM client that echoes the last user message back.

    Satisfies :class:`~lexigram.contracts.ai.llm.LLMClientProtocol` for
    development and testing without requiring a real API key.
    """

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Result[_StubCompletion, LLMError]:
        """Return a canned acknowledgement for the last user message.

        Args:
            messages: Conversation history to respond to.
            model: Ignored by the stub.
            temperature: Ignored by the stub.
            max_tokens: Ignored by the stub.

        Returns:
            ``Ok(StubCompletion)`` always.
        """
        last_user = next(
            (m.content for m in reversed(messages) if m.role == Role.USER),
            "Hello!",
        )
        return Ok(
            _StubCompletion(
                content=f"[stub] Echo: {last_user[:80]}",
                model=model or "stub",
            )
        )


class _StubEmbeddingClient:
    """Returns a fixed 4-dimensional embedding vector for any text.

    Satisfies :class:`~lexigram.contracts.ai.llm.EmbeddingClientProtocol`.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a stub embedding for each input text.

        Args:
            texts: Texts to embed.

        Returns:
            A list of fixed-dimension stub vectors (one per input).
        """
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class _StubTokenCounter:
    """Estimates token counts as one token per four characters.

    Satisfies :class:`~lexigram.contracts.ai.llm.TokenCounterProtocol`.
    """

    def count(self, text: str) -> int:
        """Estimate the token count for *text*.

        Args:
            text: Input text to estimate.

        Returns:
            Approximate token count (characters ÷ 4).
        """
        return max(1, len(text) // 4)

    def count_messages(self, messages: list[Any]) -> int:
        """Estimate the aggregate token count for a list of messages.

        Args:
            messages: Messages whose content to count.

        Returns:
            Sum of per-message token estimates.
        """
        return sum(self.count(m.content) for m in messages)


class _InMemoryVectorStore:
    """Trivial in-memory vector store with cosine-similarity stub search.

    Satisfies :class:`~lexigram.contracts.ai.vector.DocumentVectorStoreProtocol`
    for development and unit-test usage.  Documents are stored as plain dicts.
    """

    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []

    async def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> Result[list[Any], Any]:
        """Return the top-k documents as stub search results.

        Args:
            query_vector: Query embedding (ignored for stub).
            top_k: Maximum results to return.
            filters: Metadata filters (ignored for stub).
            score_threshold: Minimum score threshold (ignored for stub).

        Returns:
            ``Ok(results)`` — always succeeds for the stub.
        """
        return Ok([])  # empty store returns no results


class AIProvider(Provider):
    """Composition root — registers all AI pipeline services.

    Reads :class:`~lexigram_example_ai.config.AIConfig` and wires stub
    implementations suitable for local development.  Swap any binding in
    a subclass or via container override to use a real LLM backend.

    Args:
        config: Optional pre-built config.  A default :class:`AIConfig` is
            used when not supplied.
    """

    name = "ai_example"
    priority = ProviderPriority.APPLICATION

    def __init__(self, config: AIConfig | None = None) -> None:
        self._config = config or AIConfig()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind all AI services.

        Args:
            container: DI container registrar.
        """
        llm = _StubLLMClient()
        embedder = _StubEmbeddingClient()
        token_counter = _StubTokenCounter()
        vector_store = _InMemoryVectorStore()

        chat_pipeline = ChatPipeline(
            llm=llm,
            token_counter=token_counter,
            history_token_budget=self._config.llm_max_tokens,
        )
        rag_pipeline = RAGPipeline(
            llm=llm,
            embedder=embedder,
            vector_store=vector_store,
        )
        summarise_tool = SummariseTool(
            pipeline=rag_pipeline,
            top_k=self._config.rag_top_k,
        )

        container.instance(ChatPipeline, chat_pipeline)
        container.instance(RAGPipeline, rag_pipeline)
        container.instance(SummariseTool, summarise_tool)

        logger.info(
            "ai_provider.registered",
            llm_driver=self._config.llm_driver,
            vector_driver=self._config.vector_driver,
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No post-freeze wiring required for the stub backends.

        Args:
            container: DI container resolver.
        """
        logger.info("ai_provider.booted")


__all__ = ["AIProvider"]
