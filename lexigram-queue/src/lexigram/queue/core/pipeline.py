"""Message pipeline middleware chain."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.queue.types import BusMessage

logger = get_logger(__name__)


class MiddlewareBase(abc.ABC):
    """Base class for message pipeline middleware."""

    @abc.abstractmethod
    async def process(self, message: BusMessage, next_handler: Any) -> None:
        """Process a message and pass to the next handler.

        Args:
            message: The message to process.
            next_handler: Async callable to invoke the next middleware or terminal handler.
        """
        ...


class MessagePipeline:
    """Ordered chain of middleware around a terminal handler."""

    def __init__(self) -> None:
        """Initialize pipeline."""
        self._middleware: list[MiddlewareBase] = []

    def add(self, middleware: MiddlewareBase) -> None:
        """Add middleware to the pipeline.

        Args:
            middleware: Middleware instance to add.
        """
        self._middleware.append(middleware)

    async def execute(self, message: BusMessage, handler: Any) -> None:
        """Execute the middleware chain and terminal handler.

        Args:
            message: The message to process.
            handler: Terminal async callable to invoke after all middleware.
        """

        async def build(index: int) -> Any:
            if index >= len(self._middleware):
                return handler
            mw = self._middleware[index]

            async def next_fn(msg: BusMessage) -> None:
                inner = await build(index + 1)
                await mw.process(msg, inner)

            return next_fn

        chain = await build(0)
        await chain(message)


__all__ = ["MessagePipeline", "MiddlewareBase"]
