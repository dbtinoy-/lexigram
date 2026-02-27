"""LLM client and prompt protocols."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from dataclasses import replace as _dc_replace
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.contracts.ai.exceptions import ExtractionError, LLMError
from lexigram.contracts.ai.multimodal import MessageContent
from lexigram.contracts.ai.thinking import ThinkingConfig, ThinkingResult
from lexigram.contracts.infra import AsyncStream

if TYPE_CHECKING:
    from lexigram.contracts.ai import ToolDefinition
    from lexigram.contracts.core import HealthCheckResult
    from lexigram.contracts.core.result import Result


@runtime_checkable
class ChatMessageProtocol(Protocol):
    """Structural protocol for chat message objects.

    Any object with ``role`` and ``content`` attributes satisfies this
    protocol.  Implemented concretely by ``lexigram.ai.llm.types.ChatMessage``.
    """

    @property
    def role(self) -> Any:
        """Message role (e.g. user, assistant, system)."""

    @property
    def content(self) -> MessageContent:
        """Message content."""


@runtime_checkable
class CompletionProtocol(Protocol):
    """Structural protocol for LLM completion objects.

    Any object with ``content`` and ``model`` attributes satisfies this
    protocol.  Implemented concretely by ``lexigram.ai.llm.types.Completion``.
    """

    content: str
    """The generated completion text."""

    model: str
    """The model that produced this completion."""

    thinking: ThinkingResult | None
    """Normalised thinking/reasoning output, or ``None`` when not enabled."""

    usage: dict[str, int] | None
    """Token usage statistics (prompt, completion, total tokens) or None."""


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM client implementations.

    All LLM providers (OpenAI, Anthropic, Google, etc.) should
    implement this interface.
    """

    async def complete(
        self,
        messages: Sequence[ChatMessageProtocol],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: Sequence[ToolDefinition] | None = None,
        stop_sequences: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Result[CompletionProtocol, LLMError]:
        """Generate a completion from messages.

        Args:
            messages: List of chat messages.
            model: Optional model override.
            temperature: Optional sampling temperature.
            max_tokens: Optional max output tokens.
            tools: Optional tool definitions.
            stop_sequences: Optional list of stop sequences for early termination.
            **kwargs: Provider-specific options.

        Returns:
            ``Ok(Completion)`` on success, ``Err(LLMError)`` on recoverable failure.
        """
        ...

    def stream_chat(
        self,
        messages: list[ChatMessageProtocol],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[ToolDefinition] | None = None,
        stop_sequences: list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncStream[StreamChunk, LLMError]:
        """Start a streaming completion.

        This method returns an ``AsyncStream`` immediately (not wrapped in
        ``Result``). The stream is established lazily when iteration begins.
        Setup failures and mid-stream failures are both surfaced through the
        stream's typed error channel.

        Args:
            messages: List of chat messages.
            model: Optional model override.
            temperature: Optional sampling temperature.
            max_tokens: Optional max output tokens.
            tools: Optional tool definitions.
            stop_sequences: Optional list of stop sequences for early termination.
            **kwargs: Provider-specific options.

        Returns:
            ``AsyncStream[StreamChunk, LLMError]`` that yields chunks or
            surfaces typed errors through terminal operations (``collect()``,
            ``first()``, ``drain()``).
        """
        ...

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform a lightweight connectivity check.

        Returns:
            Structured health check result.
        """
        ...

    async def close(self) -> None:
        """Close the client and release resources."""
        ...


@runtime_checkable
class EmbeddingClientProtocol(Protocol):
    """Protocol for embedding client implementations."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        ...

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform a lightweight connectivity check.

        Returns:
            Structured health check result.
        """
        ...

    async def close(self) -> None:
        """Close the client and release resources."""
        ...


@runtime_checkable
class StructuredExtractorProtocol(Protocol):
    """Protocol for extracting typed, validated data from LLM responses.

    Implementations wrap an ``LLMClientProtocol``, instruct the model to respond
    with JSON matching a given schema, and validate the parsed response
    against a target model type.
    """

    async def extract(
        self,
        prompt: str | list[ChatMessageProtocol],
        output_model: type[Any],
        *,
        max_retries: int = 2,
        model: str | None = None,
        **kwargs: Any,
    ) -> Result[Any, ExtractionError | LLMError]:
        """Extract structured data from an LLM response.

        Args:
            prompt: Text prompt or list of chat messages.
            output_model: Model class to validate the response against.
            max_retries: Number of additional attempts on parse/validation failure.
            model: Optional LLM model name override.
            **kwargs: Extra options forwarded to the underlying LLM client.

        Returns:
            ``Ok(output_model_instance)`` on success.
            ``Err(ExtractionError)`` on parse/validation failure.
            ``Err(LLMError)`` when the underlying client returns a recoverable
            provider/model failure.
        """
        ...


@runtime_checkable
class PromptTemplateProtocol(Protocol):
    """Protocol for prompt templates that render to text or chat messages."""

    @property
    def name(self) -> str:
        """Unique name identifying this template."""
        ...

    def render(self, **kwargs: Any) -> str | list[dict[str, str]]:
        """Render the template with the supplied variable values.

        Args:
            **kwargs: Variable name → value pairs.

        Returns:
            A plain string or a list of ``{"role": ..., "content": ...}`` dicts.
        """
        ...

    def get_variables(self) -> list[str]:
        """Return the list of declared variable names."""
        ...


@runtime_checkable
class PromptRegistryProtocol(Protocol):
    """Protocol for a named template registry."""

    def register(
        self,
        name: str,
        template: PromptTemplateProtocol,
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a template under *name*."""
        ...

    def get(self, name: str) -> PromptTemplateProtocol:
        """Retrieve a template by name."""
        ...

    def list_names(self) -> list[str]:
        """Return all registered template names."""
        ...


@runtime_checkable
class TokenCounterProtocol(Protocol):
    """Model-aware token counter.

    Implementations use the exact tokenizer for the target model (tiktoken for
    OpenAI, AutoTokenizer for HuggingFace, mistral-common for Mistral). A
    character-estimate fallback is always available.

    Note: Methods are synchronous because tokenization is CPU-bound with no I/O.
    """

    def count(self, text: str) -> int:
        """Count tokens in a text string."""
        ...

    def count_messages(self, messages: list[ChatMessageProtocol]) -> int:
        """Count tokens in a list of chat messages, including message overhead."""
        ...

    @property
    def model(self) -> str:
        """The model this counter is calibrated for."""
        ...


@runtime_checkable
class PromptAssemblerProtocol(Protocol):
    """Assembles prompt layers in cache-friendly static-to-dynamic order.

    The static-first ordering maximizes provider-side KV cache reuse. The
    assembler also injects provider-specific cache annotations (Anthropic's
    cache_control breakpoints, DeepSeek's 64-token padding, etc.).
    """

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
        """Assemble a complete prompt message list.

        Args:
            system: System instructions (static, cached).
            tools: Tool/function definitions.
            reference_docs: Reference documents as text (semi-static).
            few_shot: Few-shot example messages (static, cached).
            history: Chat history messages (dynamic).
            query: Current user query (dynamic).
            provider: Provider name for cache annotation strategy.
            dynamic_metadata: Timestamps, user IDs, etc. (dynamic).

        Returns:
            Ordered list of ChatMessage instances ready for the LLM client.
        """
        ...


@runtime_checkable
class PromptRendererProtocol(Protocol):
    """Renders a prompt template with provided variables.

    Consumed by: lexigram-ai-platform prompt submodule, lexigram-ai-rag.
    """

    def render(self, template: str, variables: dict[str, Any]) -> str:
        """Render a template string with the supplied variable mapping.

        Args:
            template: The raw template string.
            variables: Mapping of variable names to their values.

        Returns:
            The rendered prompt string.
        """
        ...


@runtime_checkable
class PromptOptimizerProtocol(Protocol):
    """Optimizes a rendered prompt for a specific model.

    Consumed by: lexigram-ai-platform prompt submodule.
    """

    async def optimize(self, prompt: str, model: str, max_tokens: int) -> str:
        """Optimize a prompt for the target model and token budget.

        Args:
            prompt: The rendered prompt string to optimize.
            model: Target model identifier.
            max_tokens: Maximum token budget for the optimized prompt.

        Returns:
            The optimized prompt string.
        """
        ...


@runtime_checkable
class SemanticCacheProtocol(Protocol):
    """Embedding-based semantic similarity cache for LLM responses.

    Provides three-tier lookup: exact hash match (Tier 1), vector similarity
    match (Tier 2), and cache miss (caller invokes LLM).

    Placement note: Lives in ai/llm.py (not infra/cache/) because it carries
    AI-domain semantics (model tracking in store(), LLM response caching).
    """

    async def lookup(self, query: str) -> str | None:
        """Look up a query in the cache.

        Checks Tier 1 (exact hash) then Tier 2 (vector similarity).

        Args:
            query: The user query string.

        Returns:
            Cached response string, or ``None`` on cache miss.
        """
        ...

    async def store(self, query: str, response: str, model: str) -> None:
        """Store a query-response pair in both tiers.

        Args:
            query: The user query string.
            response: The LLM response to cache.
            model: The model that produced the response.
        """
        ...

    async def invalidate(self, query: str) -> bool:
        """Invalidate a cached entry by query.

        Args:
            query: The user query string to invalidate.

        Returns:
            ``True`` if the entry was found and removed, ``False`` otherwise.
        """
        ...


@dataclass(frozen=True)
class StreamEvent:
    """Protocol for streaming events."""

    type: str
    content: str | None = None
    tool_call: Any | None = None
    error: str | None = None


@dataclass(frozen=True)
class TokenBudget:
    """Immutable token budget that pipeline stages consult.

    Every field is calculated once at the start of a request. Stages read
    remaining capacity via properties — they never mutate the budget.
    Builder methods return new instances (immutable value semantics).
    """

    model_context_limit: int
    reserved_for_output: int
    system_prompt_tokens: int
    tool_definitions_tokens: int
    rag_context_tokens: int = 0
    history_tokens: int = 0

    @property
    def total_used(self) -> int:
        """Total tokens consumed by all components."""
        return (
            self.system_prompt_tokens
            + self.tool_definitions_tokens
            + self.rag_context_tokens
            + self.history_tokens
            + self.reserved_for_output
        )

    @property
    def remaining(self) -> int:
        """Tokens available for additional content."""
        return max(0, self.model_context_limit - self.total_used)

    @property
    def remaining_for_history(self) -> int:
        """Tokens available specifically for chat history."""
        used = (
            self.system_prompt_tokens
            + self.tool_definitions_tokens
            + self.rag_context_tokens
            + self.reserved_for_output
        )
        return max(0, self.model_context_limit - used)

    @property
    def over_budget(self) -> bool:
        """True if total consumption exceeds the model context limit."""
        return self.total_used > self.model_context_limit

    def with_rag_tokens(self, rag_tokens: int) -> TokenBudget:
        """Return a new budget with updated RAG token count."""
        return _dc_replace(self, rag_context_tokens=rag_tokens)

    def with_history_tokens(self, history_tokens: int) -> TokenBudget:
        """Return a new budget with updated history token count."""
        return _dc_replace(self, history_tokens=history_tokens)


class Role(StrEnum):
    """Concrete chat message role constants shared across AI packages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


@dataclass(frozen=True)
class ChatMessage:
    """Concrete chat message data class shared across AI packages.

    Satisfies ``ChatMessageProtocol``.  Suitable for construction in any
    package that needs to build messages without importing from
    ``lexigram-ai-llm``.
    """

    role: str
    content: MessageContent
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
    """Native tool calls requested by the LLM (assistant messages only).

    When present, the message carries the function-call requests of an
    assistant turn so the provider can re-emit them to the model before
    the matching ``tool`` role responses.
    """
    thinking_blocks: list[dict[str, Any]] | None = None
    """Raw provider thinking blocks for multi-turn re-injection.

    Anthropic: list of ``{type, thinking, signature}`` dicts from a prior
    assistant turn with extended thinking enabled.  Must be passed back
    verbatim to continue a thinking-enabled conversation.
    """
    metadata: dict[str, Any] | None = None
    """Provider-specific metadata for cache control and annotations."""


@dataclass(frozen=True)
class Completion:
    """Minimal completion data class shared across AI packages.

    Satisfies ``CompletionProtocol``.  Used by consumers that build
    fallback completions without depending on ``lexigram-ai-llm``'s
    full Pydantic model.
    """

    content: str
    model: str
    thinking: ThinkingResult | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FunctionCall:
    """Function call request from LLM."""

    name: str
    arguments: dict[str, Any] | str = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    """Tool call request from LLM."""

    id: str
    type: str = "function"
    function: FunctionCall | None = None


@dataclass(frozen=True)
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class StreamChunk:
    """A chunk of streamed completion."""

    delta: str | None = None
    model: str | None = None
    finish_reason: str | None = None
    role: str | None = None
    index: int = 0
    thinking_delta: str | None = None
    is_thinking: bool = False


@runtime_checkable
class CostEstimatorProtocol(Protocol):
    """Estimates the monetary cost of LLM usage.

    Implementations map token usage for a model/provider to a cost in
    USD.  Consumed by agents (governance cost tracking) and any package
    that reports spend.  When no estimator is wired, callers must skip
    cost tracking rather than fabricate estimates.
    """

    def estimate_cost(
        self,
        model: str,
        total_tokens: int,
        provider: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> float:
        """Estimate cost in USD for the given token usage.

        When *prompt_tokens* and *completion_tokens* are provided they are
        priced at the input and output rates respectively — this yields the
        most accurate estimate.  When both are ``0`` the caller has no
        usage split, so implementations must fall back to *total_tokens*
        using a documented approximation.

        Args:
            model: Model identifier (e.g. ``gpt-4o``).
            total_tokens: Total tokens consumed (prompt + completion).
            provider: Provider name (e.g. ``openai``) when pricing
                differs per provider.
            prompt_tokens: Input token count from ``Completion.usage``.
                Defaults to ``0`` (unknown).
            completion_tokens: Output token count from
                ``Completion.usage``.  Defaults to ``0`` (unknown).

        Returns:
            Estimated cost in USD.  Return ``0.0`` when pricing is
            unknown for the model.
        """
        ...


__all__ = [
    "AsyncStream",
    "ChatMessage",
    "ChatMessageProtocol",
    "Completion",
    "CompletionProtocol",
    "CostEstimatorProtocol",
    "EmbeddingClientProtocol",
    "ExtractionError",
    "FunctionCall",
    "LLMClientProtocol",
    "LLMError",
    "PromptAssemblerProtocol",
    "PromptOptimizerProtocol",
    "PromptRegistryProtocol",
    "PromptRendererProtocol",
    "PromptTemplateProtocol",
    "Role",
    "SemanticCacheProtocol",
    "StreamChunk",
    "StreamEvent",
    "StructuredExtractorProtocol",
    "ThinkingConfig",
    "ThinkingResult",
    "TokenBudget",
    "TokenCounterProtocol",
    "TokenUsage",
    "ToolCall",
]
