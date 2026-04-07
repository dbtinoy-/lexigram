"""Feedback module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.feedback import FeedbackProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.feedback.config import FeedbackConfig


@module()
class FeedbackModule(Module):
    """AI Feedback collection and processing integration.

    Call :meth:`configure` to register a
    :class:`~lexigram.contracts.ai.feedback.FeedbackProtocol` implementation
    along with the processor registry and storage backend for injection.

    Usage::

        from lexigram.ai.feedback.config import FeedbackConfig

        @module(
            imports=[
                FeedbackModule.configure(
                    FeedbackConfig(storage="database")
                )
            ]
        )
        class AppModule(Module):
            pass

    Error Handling::

        The feedback services use the Result pattern for expected failures.
        Domain errors are available via the exported exception hierarchy::

            from lexigram.ai.feedback.exceptions import (
                FeedbackError,           # base — catch-all
                FeedbackProcessingError, # processor pipeline failure
                FeedbackValidationError, # schema / data-validation failure
            )

    Exports:
        :class:`~lexigram.contracts.ai.feedback.FeedbackProtocol`,
        :class:`~lexigram.ai.feedback.exceptions.FeedbackError`,
        :class:`~lexigram.ai.feedback.exceptions.FeedbackProcessingError`,
        :class:`~lexigram.ai.feedback.exceptions.FeedbackValidationError`
    """

    @classmethod
    def configure(cls, config: FeedbackConfig | None = None) -> DynamicModule:
        """Create a FeedbackModule with the given configuration.

        Args:
            config: :class:`~lexigram.ai.feedback.config.FeedbackConfig`, a
                plain ``dict`` of the same keys, or ``None`` to read from
                environment variables.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.feedback.di.provider import FeedbackProvider

        return DynamicModule(
            module=cls,
            providers=[FeedbackProvider(config=config)],
            exports=[
                FeedbackProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: FeedbackConfig | None = None) -> DynamicModule:
        """Create a FeedbackModule suitable for unit and integration testing.

        Uses in-memory or no-op implementations with minimal side effects.

        Args:
            config: Optional config override. Uses safe test defaults when None.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.feedback.di.provider import FeedbackProvider

        return DynamicModule(
            module=cls,
            providers=[FeedbackProvider(config=config)],
            exports=[
                FeedbackProtocol,
            ],
        )


__all__ = ["FeedbackModule"]
