"""Multi-turn chat pipeline.

Wraps an :class:`~lexigram.contracts.ai.llm.LLMClientProtocol` to provide
a stateless, token-aware multi-turn completion interface.  History is passed
in by the caller — the pipeline never stores state, making it safe to share
a single instance across concurrent requests.

Pattern demonstrated:
- Constructor injection of ``LLMClientProtocol`` and ``TokenCounterProtocol``
- ``Result[T, E]`` return type for all I/O operations
- History truncation to respect the token budget
- Structured logging with key-value pairs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lexigram.contracts.ai.llm import (
    ChatMessage,
    LLMClientProtocol,
    Role,
    TokenCounterProtocol,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_ai.domain.conversation import Conversation, MessageRole

if TYPE_CHECKING:
    from lexigram.contracts.ai.exceptions import LLMError

logger = get_logger(__name__)

# Maximum tokens reserved for conversation history.  Completions are capped at
# ``llm_max_tokens``; the system prompt consumes a small slice on top of that.
_DEFAULT_HISTORY_TOKEN_BUDGET = 6_000


@dataclass(frozen=True)
class ChatRequest:
    """Input for a single chat turn.

    Attributes:
        conversation: The full conversation entity including prior history.
        user_message: The new user message to respond to.
        system_prompt: Optional system-level instructions.  Defaults to a
            general assistant prompt when not supplied.
        model: Optional model override.  Falls back to the provider default.
        temperature: Optional sampling temperature override.
        max_tokens: Optional maximum output token count override.
    """

    conversation: Conversation
    user_message: str
    system_prompt: str = (
        "You are a helpful, accurate, and concise AI assistant."
    )
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ChatResponse:
    """Output of a successful chat turn.

    Attributes:
        content: The assistant's reply text.
        model: The model that generated the reply.
        conversation_id: The conversation entity ID this turn belongs to.
        history_tokens: Token count of the history slice sent to the LLM.
    """

    content: str
    model: str
    conversation_id: str
    history_tokens: int = 0


class ChatPipeline:
    """Stateless multi-turn chat pipeline backed by an LLM client.

    Builds a prompt from the conversation history, trims it to fit the token
    budget, calls the LLM, and returns a typed result.  It never mutates the
    supplied :class:`~lexigram_example_ai.domain.conversation.Conversation` —
    callers are responsible for appending the assistant reply.

    Args:
        llm: LLM client satisfying :class:`~lexigram.contracts.ai.llm.LLMClientProtocol`.
        token_counter: Token counter for the target model.
        history_token_budget: Maximum tokens to allocate for conversation history.
            Older messages are dropped (oldest-first) when the budget is exceeded.
    """

    def __init__(
        self,
        llm: LLMClientProtocol,
        token_counter: TokenCounterProtocol,
        history_token_budget: int = _DEFAULT_HISTORY_TOKEN_BUDGET,
    ) -> None:
        self._llm = llm
        self._token_counter = token_counter
        self._history_token_budget = history_token_budget

    async def run(
        self,
        request: ChatRequest,
    ) -> Result[ChatResponse, LLMError]:
        """Execute a single chat turn.

        Assembles the message list from conversation history, applies token
        budget trimming, calls the LLM, and returns the assistant reply.

        Args:
            request: Chat request containing the conversation and new message.

        Returns:
            ``Ok(ChatResponse)`` on success, ``Err(LLMError)`` on failure.
        """
        messages = self._build_messages(request)
        history_tokens = self._token_counter.count_messages(messages)

        logger.info(
            "chat_pipeline.running",
            conversation_id=request.conversation.id,
            history_messages=len(messages),
            history_tokens=history_tokens,
            model=request.model or "default",
        )

        result = await self._llm.complete(
            messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        if result.is_err():
            error = result.unwrap_err()
            logger.warning(
                "chat_pipeline.llm_error",
                conversation_id=request.conversation.id,
                error=str(error),
            )
            return Err(error)

        completion = result.unwrap()

        logger.info(
            "chat_pipeline.completed",
            conversation_id=request.conversation.id,
            model=completion.model,
            content_length=len(completion.content),
        )

        return Ok(
            ChatResponse(
                content=completion.content,
                model=completion.model,
                conversation_id=request.conversation.id,
                history_tokens=history_tokens,
            )
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_messages(self, request: ChatRequest) -> list[ChatMessage]:
        """Assemble the ordered message list for the LLM, trimmed to budget.

        The system prompt is always included first.  History messages are
        included newest-first until the token budget is consumed, then the
        new user message is appended last.

        Args:
            request: The chat request containing history and new message.

        Returns:
            Ordered list of :class:`~lexigram.contracts.ai.llm.ChatMessage`.
        """
        system_msg = ChatMessage(role=Role.SYSTEM, content=request.system_prompt)

        # Convert domain history to ChatMessage objects
        history: list[ChatMessage] = [
            ChatMessage(
                role=Role.ASSISTANT
                if msg.role == MessageRole.ASSISTANT
                else Role.USER,
                content=msg.content,
            )
            for msg in request.conversation.messages
        ]

        # Trim history to fit the token budget (oldest messages dropped first)
        trimmed = self._trim_to_budget(history)
        history_tokens = self._token_counter.count_messages(trimmed)

        user_msg = ChatMessage(role=Role.USER, content=request.user_message)

        logger.debug(
            "chat_pipeline.history_trimmed",
            original=len(history),
            trimmed=len(trimmed),
            history_tokens=history_tokens,
        )

        return [system_msg, *trimmed, user_msg]

    def _trim_to_budget(
        self,
        messages: list[ChatMessage],
    ) -> list[ChatMessage]:
        """Drop the oldest messages until the history fits the token budget.

        Args:
            messages: Full history in chronological order.

        Returns:
            Trimmed history list that fits within ``_history_token_budget``.
        """
        if not messages:
            return []

        # Walk from oldest to newest, keeping the tail that fits the budget.
        for start in range(len(messages)):
            candidate = messages[start:]
            if self._token_counter.count_messages(candidate) <= self._history_token_budget:
                return candidate

        # Even a single message may exceed budget — return the last one only.
        return messages[-1:]


__all__ = [
    "ChatPipeline",
    "ChatRequest",
    "ChatResponse",
]
