"""LLM module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai import LLMClientProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.llm.config import ClientConfig
    from lexigram.ai.llm.routing.config import LLMConfig


@module()
class LLMModule(Module):
    """LLM client and model-management integration.

    Call :meth:`configure` to register an :class:`~lexigram.contracts.ai.LLMClientProtocol`
    implementation and optional model manager for injection.

    Usage::

        from lexigram.ai.llm.config import ClientConfig

        @module(
            imports=[
                LLMModule.configure(
                    ClientConfig(provider="openai", model="gpt-4o")
                )
            ]
        )
        class AppModule(Module):
            pass

    Multi-provider routing::

        from lexigram.ai.llm import LLMModule

        @module(
            imports=[LLMModule.configure(routing=LLMConfig())]
        )
        class AppModule(Module):
            pass
    """

    @classmethod
    def configure(
        cls,
        config: ClientConfig | Any | None = None,
        *,
        routing: LLMConfig | Any | None = None,
        enable_model_manager: bool = False,
        enable_streaming: bool = True,
        audit_calls: bool = False,
    ) -> DynamicModule:
        """Create an LLMModule with a single configured provider.

        Args:
            config: :class:`~lexigram.ai.llm.config.ClientConfig` or ``None``
                to read configuration from environment variables.
            routing: Optional :class:`~lexigram.ai.llm.routing.config.LLMConfig`
                enabling the multi-provider routing layer instead of the
                single-provider client.
            enable_model_manager: Register :class:`~lexigram.ai.llm.model_manager.LLMModelManager`
                for local model lifecycle control.
            enable_streaming: Enable streaming response support. Defaults to
                ``True``; set to ``False`` to restrict to non-streaming clients only.
            audit_calls: Emit an ``AuditEntry`` per LLM completion via
                :class:`~lexigram.ai.llm.audit_bridge.LLMAuditBridge`. Requires
                ``AuditLoggerProtocol`` in the container. Default ``False``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        if routing is not None:
            from lexigram.ai.llm.di.routing_provider import LLMRoutingProvider

            return DynamicModule(
                module=cls,
                providers=[LLMRoutingProvider(config=routing)],
                exports=[LLMClientProtocol],
            )

        from lexigram.ai.llm.di.provider import LLMProvider

        return DynamicModule(
            module=cls,
            providers=[
                LLMProvider(
                    config=config,
                    enable_model_manager=enable_model_manager,
                    enable_streaming=enable_streaming,
                    audit_calls=audit_calls,
                )
            ],
            exports=[LLMClientProtocol],
        )

    @classmethod
    def stub(cls, config: ClientConfig | Any | None = None) -> DynamicModule:
        """Create an LLMModule suitable for unit and integration testing.

        Uses a no-op or stub LLM client with minimal external dependencies.
        Streaming is disabled by default to simplify test assertions.

        Args:
            config: Optional :class:`~lexigram.ai.llm.config.ClientConfig` override.
                Uses safe test defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.llm.di.provider import LLMProvider

        return DynamicModule(
            module=cls,
            providers=[
                LLMProvider(
                    config=config,
                    enable_model_manager=False,
                    enable_streaming=False,
                )
            ],
            exports=[LLMClientProtocol],
        )


__all__ = ["LLMModule"]
