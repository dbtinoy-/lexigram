"""MCP module for Lexigram."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.mcp.config import MCPConfig


@module(name="lexigram-ai-mcp")
class MCPModule(Module):
    """Module for MCP server.

    Provides MCP server, handlers, and transports to the application.

    Usage::

        app = LexigramApplication(
            modules=[..., MCPModule.configure()],
        )

        # With MCPController subclasses::

        app = LexigramApplication(
            modules=[..., MCPModule.configure(controllers=[DataToolsController])],
        )

        # Auto-expose existing services as MCP tools::

        app = LexigramApplication(
            modules=[
                ...,
                MCPModule.from_services(
                    services=[UserService, AnalyticsService],
                    include_methods=["search", "get_*"],
                ),
            ],
        )
    """

    @classmethod
    def from_services(
        cls,
        services: list[type],
        *,
        include_methods: list[str] | None = None,
        config: MCPConfig | None = None,
    ) -> DynamicModule:
        """Create an MCPModule that auto-exposes service methods as MCP tools.

        Args:
            services: Service classes whose public methods are exposed as tools.
            include_methods: Optional glob patterns to restrict which methods are
                exposed (e.g. ``["search", "get_*"]``).
            config: Optional :class:`~lexigram.ai.mcp.config.MCPConfig` override.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        return cls.configure(
            config=config,
            services=services,
            include_methods=include_methods,
        )

    @classmethod
    def configure(
        cls,
        *,
        config: MCPConfig | None = None,
        controllers: list[type] | None = None,
        services: list[type] | None = None,
        include_methods: list[str] | None = None,
        enable_streaming: bool = True,
        **provider_kwargs: Any,
    ) -> DynamicModule:
        """Create an MCPModule with explicit provider configuration.

        Args:
            config: Optional :class:`~lexigram.ai.mcp.config.MCPConfig`.
            controllers: :class:`~lexigram.ai.mcp.controllers.MCPController`
                subclasses to register with the server.
            services: Service classes to auto-expose as MCP tools.
            include_methods: Glob patterns to restrict auto-exposed methods.
            enable_streaming: Enable SSE streaming transport support. Defaults
                to ``True``; set to ``False`` to restrict the server to
                stdio-only transport.
            **provider_kwargs: Additional keyword arguments forwarded to
                :class:`~lexigram.ai.mcp.di.provider.MCPProvider`.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.mcp.di.provider import MCPProvider
        from lexigram.ai.mcp.server import MCPServer

        return DynamicModule(
            module=cls,
            providers=[
                MCPProvider(
                    config=config,
                    controllers=controllers,
                    services=services,
                    include_methods=include_methods,
                    enable_streaming=enable_streaming,
                    **provider_kwargs,
                )
            ],
            exports=[MCPServer],
        )

    @classmethod
    def stub(cls, config: MCPConfig | None = None) -> DynamicModule:
        """Create an MCPModule suitable for unit and integration testing.

        Uses in-memory transport with no external MCP server connections.
        Streaming is disabled by default to simplify test assertions.

        Args:
            config: Optional :class:`~lexigram.ai.mcp.config.MCPConfig`
                override. Uses safe test defaults when ``None``.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.mcp.di.provider import MCPProvider
        from lexigram.ai.mcp.server import MCPServer

        return DynamicModule(
            module=cls,
            providers=[MCPProvider(config=config, enable_streaming=False)],
            exports=[MCPServer],
        )


__all__ = ["MCPModule"]
