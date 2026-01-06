"""CLI shell context factories for lexigram-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_ai_client(container: ContainerResolverProtocol) -> object:
    """Provide an AI client for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved AI client instance.
    """
    from lexigram.contracts.ai.llm import LLMClientProtocol

    return await container.resolve(LLMClientProtocol)
