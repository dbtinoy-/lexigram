"""Callback manager implementation for AI observability."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.callbacks import (
    CallbackHandlerProtocol,
)
from lexigram.contracts.ai.llm import ChatMessage, Completion
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class CallbackManagerImpl:
    """Implementation of CallbackManagerProtocol.

    Manages callback handlers and fans out events to all registered
    handlers. Supports parent-child hierarchy for run-scoped propagation.
    Handler failures are isolated to prevent breaking other handlers.
    """

    def __init__(self, parent: CallbackManagerImpl | None = None) -> None:
        """Initialize the callback manager.

        Args:
            parent: Optional parent manager for child creation.
        """
        self._parent = parent
        self._handlers: list[CallbackHandlerProtocol] = []
        if parent is not None:
            self._handlers = list(parent._handlers)

    def register(self, handler: CallbackHandlerProtocol) -> None:
        """Register a callback handler.

        Args:
            handler: The handler to register.
        """
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unregister(self, handler: CallbackHandlerProtocol) -> None:
        """Unregister a callback handler.

        Args:
            handler: The handler to remove.
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    def child(self, run_id: str) -> CallbackManagerImpl:
        """Create a child callback manager for a specific run.

        Args:
            run_id: Unique identifier for this run.

        Returns:
            A child CallbackManagerImpl instance.
        """
        return CallbackManagerImpl(parent=self)

    async def on_llm_start(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call starts."""
        await self._fanout("on_llm_start", messages=messages, model=model, **kwargs)

    async def on_llm_new_token(
        self,
        token: str,
        **kwargs: Any,
    ) -> None:
        """Called for each new token in a streaming LLM response."""
        await self._fanout("on_llm_new_token", token=token, **kwargs)

    async def on_llm_end(
        self,
        response: Completion,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call completes successfully."""
        await self._fanout("on_llm_end", response=response, **kwargs)

    async def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM call fails."""
        await self._fanout("on_llm_error", error=error, **kwargs)

    async def on_chain_start(
        self,
        name: str,
        inputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain/pipeline starts executing."""
        await self._fanout("on_chain_start", name=name, inputs=inputs, **kwargs)

    async def on_chain_end(
        self,
        name: str,
        outputs: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain/pipeline completes."""
        await self._fanout("on_chain_end", name=name, outputs=outputs, **kwargs)

    async def on_tool_start(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts executing."""
        await self._fanout(
            "on_tool_start", tool_name=tool_name, arguments=arguments, **kwargs
        )

    async def on_tool_end(
        self,
        tool_name: str,
        result: Any,
        **kwargs: Any,
    ) -> None:
        """Called when a tool finishes executing."""
        await self._fanout("on_tool_end", tool_name=tool_name, result=result, **kwargs)

    async def on_agent_action(
        self,
        action: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when an agent takes an action."""
        await self._fanout("on_agent_action", action=action, **kwargs)

    async def on_agent_finish(
        self,
        response: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when an agent finishes executing."""
        await self._fanout("on_agent_finish", response=response, **kwargs)

    async def on_retriever_start(
        self,
        query: str,
        **kwargs: Any,
    ) -> None:
        """Called when a retriever starts a search."""
        await self._fanout("on_retriever_start", query=query, **kwargs)

    async def on_retriever_end(
        self,
        documents: list[Any],
        **kwargs: Any,
    ) -> None:
        """Called when a retriever completes a search."""
        await self._fanout("on_retriever_end", documents=documents, **kwargs)

    async def _fanout(
        self,
        method_name: str,
        **kwargs: Any,
    ) -> None:
        """Fan out a callback to all registered handlers.

        Failures in individual handlers are isolated to prevent
        breaking the entire chain.

        Args:
            method_name: Name of the callback method to invoke.
            **kwargs: Arguments to pass to the callback.
        """
        for handler in self._handlers:
            try:
                method = getattr(handler, method_name)
                await method(**kwargs)
            except Exception as e:
                logger.warning(
                    "Callback handler failed",
                    handler=handler.__class__.__name__,
                    method=method_name,
                    error=str(e),
                )


__all__ = ["CallbackManagerImpl"]
