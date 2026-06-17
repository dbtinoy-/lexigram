"""No-op LLM client for testing and stubbed deployments."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from lexigram.ai.llm.clients.base import AbstractLLMClient
from lexigram.ai.llm.config import ClientConfig
from lexigram.ai.llm.exceptions import LLMError
from lexigram.ai.llm.types import Completion
from lexigram.contracts.ai import ChatMessage, ToolCall
from lexigram.contracts.ai.llm import StreamChunk
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.result import Ok, Result


class NoOpLLMClient(AbstractLLMClient):
    """LLM client that never talks to a provider.

    Every call resolves to a deterministic, in-memory response so the
    subsystem can boot and be exercised without SDK credentials.
    """

    def __init__(self, config: ClientConfig | None = None) -> None:
        super().__init__(config or ClientConfig())

    async def _do_complete(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> Result[Completion, LLMError]:
        return Ok(
            Completion(
                content="",
                model=self.config.model,
                usage=None,
            )
        )

    async def _do_stream_chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> Result[AsyncIterator[StreamChunk], LLMError]:
        async def _empty() -> AsyncIterator[StreamChunk]:
            if False:
                yield

        return Ok(_empty())

    async def _do_chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolCall] | None = None,
        **kwargs: Any,
    ) -> Result[Completion, LLMError]:
        return await self._do_complete(messages, **kwargs)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(status=HealthStatus.OK)


__all__ = ["NoOpLLMClient"]
