"""SkillsModule — convenience façade for integrating the skills subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.skills import SkillExecutorProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.skills.config import SkillsConfig


@module()
class SkillsModule(Module):
    """Application-level façade for the skills subsystem.

    Provides a ``configure`` factory that creates a pre-configured
    :class:`SkillsProvider` ready for registration with the application
    container.

    Usage::

        from lexigram.ai.skills import SkillsModule
        from lexigram.ai.skills.config import SkillsConfig

        @module(
            imports=[SkillsModule.configure(
                SkillsConfig(
                    enable_builtin=True,
                    builtin_skills=["current_datetime", "math_calculate"],
                )
            )]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: SkillsConfig | None = None,
        enable_tool_bridge: bool = False,
        **kwargs: Any,
    ) -> DynamicModule:
        """Create a SkillsModule with explicit configuration.

        Args:
            config: :class:`SkillsConfig` or ``None`` to use defaults.
            enable_tool_bridge: Register the tool-bridge adapter so agent tool
                registries can invoke skills as first-class tools. Defaults to
                ``False``.
            **kwargs: Additional keyword arguments forwarded to
                :class:`SkillsProvider`.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.skills.di.provider import SkillsProvider

        return DynamicModule(
            module=cls,
            providers=[
                SkillsProvider(
                    config=config,
                    enable_tool_bridge=enable_tool_bridge,
                    **kwargs,
                )
            ],
            exports=[
                SkillExecutorProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: SkillsConfig | None = None) -> DynamicModule:
        """Create a SkillsModule suitable for unit and integration testing.

        Uses in-memory or no-op skill implementations with minimal side
        effects. Built-in skill registration is disabled by default to keep
        the test container lightweight.

        Args:
            config: Optional :class:`SkillsConfig` override. Uses safe test
                defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.skills.di.provider import SkillsProvider

        return DynamicModule(
            module=cls,
            providers=[SkillsProvider(config=config, enable_tool_bridge=False)],
            exports=[
                SkillExecutorProtocol,
            ],
        )


__all__ = ["SkillsModule"]
