"""Prompt module for Lexigram."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.llm import PromptTemplateProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.prompt.config import PromptConfig


@module()
class PromptModule(Module):
    """Prompt template management and rendering integration.

    Registers the :class:`~lexigram.ai.prompt.di.provider.PromptProvider`
    which wires a :class:`~lexigram.ai.prompt.registry.registry.PromptRegistry`
    into the container and exposes it as
    :class:`~lexigram.contracts.ai.llm.PromptTemplateProtocol`.

    Usage::

        from lexigram.ai.prompt import PromptModule
        from lexigram.ai.prompt.config import PromptConfig

        @module(
            imports=[
                PromptModule.configure(
                    PromptConfig(default_format="jinja2")
                )
            ]
        )
        class AppModule(Module):
            pass

    Error Handling::

        Prompt rendering and registry lookups surface typed exceptions that
        can be caught directly or handled via the Result pattern::

            from lexigram.ai.prompt.exceptions import (
                PromptError,          # base — catch-all
                PromptRenderError,    # template rendering failure
                PromptValidationError,# variable type / value validation
                PromptNotFoundError,  # named template not in registry
                PromptVersionError,   # version conflict or invalid rollback
            )

    Exports:
        :class:`~lexigram.contracts.ai.llm.PromptTemplateProtocol`,
        :class:`~lexigram.ai.prompt.exceptions.PromptError`,
        :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`,
        :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`,
        :class:`~lexigram.ai.prompt.exceptions.PromptNotFoundError`,
        :class:`~lexigram.ai.prompt.exceptions.PromptVersionError`
    """

    @classmethod
    def configure(
        cls, config: PromptConfig | None = None, **kwargs: Any
    ) -> DynamicModule:
        """Create a PromptModule with explicit configuration.

        Args:
            config: :class:`~lexigram.ai.prompt.config.PromptConfig` or ``None``
                to use defaults.
            **kwargs: Additional keyword arguments forwarded to
                :class:`~lexigram.ai.prompt.di.provider.PromptProvider`.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.prompt.di.provider import PromptProvider

        return DynamicModule(
            module=cls,
            providers=[PromptProvider(config=config, **kwargs)],
            exports=[
                PromptTemplateProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: PromptConfig | None = None) -> DynamicModule:
        """Create a PromptModule suitable for unit and integration testing.

        Uses in-memory or no-op implementations with minimal side effects.

        Args:
            config: Optional config override. Uses safe test defaults when None.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.prompt.di.provider import PromptProvider

        return DynamicModule(
            module=cls,
            providers=[PromptProvider(config=config)],
            exports=[
                PromptTemplateProtocol,
            ],
        )


__all__ = ["PromptModule"]
