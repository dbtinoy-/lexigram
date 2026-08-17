"""Cache-aware prompt assembler implementing PromptAssemblerProtocol."""

from __future__ import annotations

from lexigram.ai.prompt.assembly.cache_strategies import ProviderCacheStrategyRegistry
from lexigram.contracts.ai import ToolDefinition
from lexigram.contracts.ai.llm import (
    ChatMessage,
    PromptAssemblerProtocol,
    TokenCounterProtocol,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class CacheAwarePromptAssembler:
    """Prompt assembler that enforces static-before-dynamic ordering and
    applies provider-specific cache annotations.

    Implements PromptAssemblerProtocol and enforces the 7-layer ordering:
    1. System instructions (STATIC)
    2. Tool/function definitions (STATIC)
    3. Reference documents (SEMI-STATIC)
    4. Few-shot examples (STATIC)
    ── CACHE BOUNDARY ──
    5. Chat history (DYNAMIC)
    6. Current user query (DYNAMIC)
    7. Dynamic metadata (DYNAMIC)

    Args:
        strategy_registry: Provider cache strategy registry.
        token_counter: Optional token counter for cache-size validation.
    """

    def __init__(
        self,
        strategy_registry: ProviderCacheStrategyRegistry,
        token_counter: TokenCounterProtocol | None = None,
    ) -> None:
        """Initialize with strategy registry and optional token counter."""
        self._registry = strategy_registry
        self._token_counter = token_counter

    def set_token_counter(self, counter: TokenCounterProtocol) -> None:
        """Inject token counter after construction (called from DI boot phase).

        Args:
            counter: Token counter to use for cache size validation.
        """
        self._token_counter = counter

    def assemble(
        self,
        system: str,
        tools: list[ToolDefinition] | None,
        reference_docs: list[str] | None,
        few_shot: list[ChatMessage] | None,
        history: list[ChatMessage],
        query: str,
        provider: str,
        dynamic_metadata: str | None = None,
    ) -> list[ChatMessage]:
        """Assemble messages in canonical static-before-dynamic order.

        This method matches the PromptAssemblerProtocol.assemble() signature
        exactly. It enforces the 7-layer static-to-dynamic ordering:

        Layers 1-4 (STATIC) come before cache boundary:
        - Layer 1: System instructions
        - Layer 2: Tool definitions
        - Layer 3: Reference documents
        - Layer 4: Few-shot examples

        Layers 5-7 (DYNAMIC) come after cache boundary:
        - Layer 5: Chat history
        - Layer 6: Current user query
        - Layer 7: Dynamic metadata

        Args:
            system: System instructions (Layer 1, always static).
            tools: Tool definitions as list of ToolDefinition objects.
            reference_docs: Reference document strings (Layer 3).
            few_shot: Few-shot example messages (Layer 4, static).
            history: Chat history messages (Layer 5, dynamic).
            query: Current user query text (Layer 6, dynamic).
            provider: Provider key for cache strategy selection.
            dynamic_metadata: Dynamic metadata string appended after query.

        Returns:
            Assembled and cache-annotated list of ChatMessage objects.
        """
        messages: list[ChatMessage] = []

        # Layer 1: System instructions (STATIC)
        if system:
            messages.append(ChatMessage(role="system", content=system))

        # Layer 2: Tool definitions (STATIC) — append as system context
        if tools:
            tool_lines: list[str] = []
            for tool in tools:
                if isinstance(tool, str):
                    tool_lines.append(tool)
                elif hasattr(tool, "name") and hasattr(tool, "description"):
                    tool_lines.append(f"Tool: {tool.name}\n{tool.description}")
                else:
                    tool_lines.append(str(tool))
            if tool_lines:
                tool_text = "\n".join(tool_lines)
                messages.append(
                    ChatMessage(role="system", content=f"Available tools:\n{tool_text}")
                )

        # Layer 3: Reference documents (SEMI-STATIC)
        if reference_docs:
            doc_text = "\n\n".join(reference_docs)
            messages.append(
                ChatMessage(role="system", content=f"Reference documents:\n{doc_text}")
            )

        # Layer 4: Few-shot examples (STATIC)
        if few_shot:
            messages.extend(few_shot)

        # Track static boundary (layers 1-4)
        static_count = len(messages)

        # Layer 5: Chat history (DYNAMIC)
        if history:
            messages.extend(history)

        # Layer 6: Current user query (DYNAMIC)
        messages.append(ChatMessage(role="user", content=query))

        # Layer 7: Dynamic metadata (DYNAMIC) — appended last
        if dynamic_metadata:
            messages.append(
                ChatMessage(role="system", content=f"Metadata: {dynamic_metadata}")
            )

        # Apply provider-specific cache annotations to static layers
        strategy = self._registry.for_provider(provider)
        messages = strategy.annotate(messages, static_count, self._token_counter)

        logger.debug(
            "prompt_assembled",
            provider=provider,
            static_layers=static_count,
            total_messages=len(messages),
        )
        return messages


# Runtime structural protocol verification for PromptAssemblerProtocol
_: PromptAssemblerProtocol = CacheAwarePromptAssembler.__new__(
    CacheAwarePromptAssembler
)
