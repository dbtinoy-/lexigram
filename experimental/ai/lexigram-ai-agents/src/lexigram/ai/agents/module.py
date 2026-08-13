"""Agents module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai import AgentExecutorProtocol, ToolRegistryProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.agents.config import AgentConfig


@module
class AgentsModule(Module):
    """Agent system module for Lexigram applications.

    Provides agent execution, tool registry, and strategy support.

    Usage::

        from lexigram.ai.agents import AgentsModule
        from lexigram.ai.agents.config import AgentConfig

        @module(
            imports=[AgentsModule.configure(AgentConfig(...))]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: AgentConfig | None = None,
        enable_multi_agent: bool = False,
    ) -> DynamicModule:
        """Create an AgentsModule with explicit configuration.

        Args:
            config: :class:`~lexigram.ai.agents.config.AgentConfig` or ``None``
                for defaults.
            enable_multi_agent: Enable multi-agent orchestration support,
                allowing agents to delegate tasks to peer agents. Defaults to
                ``False``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.agents.di.provider import AgentsProvider

        return DynamicModule(
            module=cls,
            providers=[
                AgentsProvider(config=config, enable_multi_agent=enable_multi_agent)
            ],
            exports=[
                AgentExecutorProtocol,
                ToolRegistryProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: AgentConfig | None = None) -> DynamicModule:
        """Create an AgentsModule suitable for unit and integration testing.

        Uses in-memory or no-op agent implementations with minimal side
        effects. Multi-agent orchestration is disabled by default to keep
        the test container lightweight.

        Args:
            config: Optional :class:`~lexigram.ai.agents.config.AgentConfig`
                override. Uses safe test defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.agents.di.provider import AgentsProvider

        return DynamicModule(
            module=cls,
            providers=[AgentsProvider(config=config, enable_multi_agent=False)],
            exports=[
                AgentExecutorProtocol,
                ToolRegistryProtocol,
            ],
        )


__all__ = ["AgentsModule"]
