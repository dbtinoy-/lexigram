"""AI orchestration module for dependency injection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai import AIProviderProtocol
from lexigram.di.module import DynamicModule, Module, module


@module()
class AIModule(Module):
    """Core AI layer: LLM orchestration, RAG pipelines, and governance.

    Call :meth:`configure` to configure the AI subsystem.  Sub-modules such as
    :class:`~lexigram.ai.llm.LLMModule` and
    :class:`~lexigram.ai.rag.RAGModule` may be imported independently
    for more granular control.

    Usage::

        from lexigram.ai.config import AIConfig
        from lexigram.ai.llm.config import ClientConfig

        @module(
            imports=[
                AIModule.configure(
                    AIConfig(llm=ClientConfig(provider="openai", model="gpt-4o"))
                )
            ]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(cls, config: Any | None = None, **kwargs: Any) -> DynamicModule:
        """Create an AIModule with explicit configuration.

        Args:
            config: :class:`~lexigram.ai.config.AIConfig` or ``None``
                for framework defaults.
            **kwargs: Additional keyword arguments forwarded to
                :class:`~lexigram.ai.di.provider.AIProvider`.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.di.provider import AIProvider

        return DynamicModule(
            module=cls,
            providers=[AIProvider(config=config, **kwargs)],
            exports=[AIProviderProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a no-op AIModule for testing.

        Registers all AI sub-modules with their testing stubs: agents,
        LLM, RAG, memory, prompts, skills, sessions, feedback, governance,
        and guards with minimal side effects.

        Returns:
            A DynamicModule with all AI sub-modules in testing configuration.
        """
        from importlib.metadata import entry_points

        from lexigram.di.module import DynamicModule

        stub_imports: list[Any] = []
        for ep in entry_points(group="lexigram.ai.modules"):
            try:
                module_cls = ep.load()
                stub_imports.append(module_cls.stub())
            except (AttributeError, ImportError, RuntimeError):
                pass

        return DynamicModule(
            module=cls,
            imports=stub_imports,
            exports=[AIProviderProtocol],
        )


__all__ = ["AIModule"]
