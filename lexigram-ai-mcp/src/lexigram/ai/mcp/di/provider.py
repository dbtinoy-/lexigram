"""MCP provider for Lexigram dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.mcp.config import MCPConfig
from lexigram.ai.mcp.exceptions import MCPInitializationError
from lexigram.ai.mcp.server import MCPServer
from lexigram.ai.mcp.server.handlers import (
    LoggingHandler,
    PromptHandler,
    ResourceHandler,
    SamplingHandler,
    ToolHandler,
)
from lexigram.ai.mcp.transport import SSETransport, StdioTransport
from lexigram.contracts import (
    ProviderPriority,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.exceptions import UnresolvableDependencyError
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class _ConnectorToolBundle:
    """Sentinel DI type: combined tool provider for all built-in connectors."""


class _ConnectorResourceBundle:
    """Sentinel DI type: combined resource provider for all built-in connectors."""


class MCPProvider(Provider):
    name = "mcp"
    priority = ProviderPriority.PRESENTATION
    config_key: str | None = "ai_mcp"
    config_model: type | None = MCPConfig

    """Provider for MCP server components.

    Registers MCP server, handlers, and transports with the DI container.
    When ``MCPConfig.client_stdio_command`` or ``MCPConfig.client_url`` is
    set, an :class:`~lexigram.ai.mcp.client.MCPClient` is also registered.

    When ``controllers`` is provided (typically set by ``MCPModule``), the
    controller instances are registered as tool/resource/prompt providers
    before the handlers are wired up.
    """

    def __init__(
        self,
        config: MCPConfig | None = None,
        controllers: list[type] | None = None,
        services: list[type] | None = None,
        include_methods: list[str] | None = None,
        enable_streaming: bool = True,
        **provider_kwargs: Any,
    ) -> None:
        super().__init__()
        self._requested_config = config
        self._config = config or MCPConfig()
        self._controllers: list[type] = controllers or []
        self._services: list[type] = services or []
        self._include_methods: list[str] | None = include_methods
        self._enable_streaming = enable_streaming
        self._managed_transports: list[StdioTransport | SSETransport] = []
        self._managed_client: Any | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register MCPConfig with the DI container."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), MCPConfig)
            else self._config
        )
        container.singleton(MCPConfig, self._config)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire up all MCP components using the resolved container."""
        if not self._config.enabled:
            return

        if self._controllers:
            await self._boot_controller_providers(container)
        if self._services:
            await self._boot_service_providers(container)
        await self._boot_skill_bridge(container)
        await self._boot_connectors(container)
        await self._boot_handlers(container)
        await self._boot_server(container)
        self._boot_transports(container)
        await self._boot_client(container)

    async def _boot_controller_providers(
        self, container: BootContainerProtocol
    ) -> None:
        """Instantiate MCPController classes and register compound providers.

        Controllers are resolved via the DI container when possible so that
        constructor dependencies are injected automatically.
        """
        from lexigram.ai.mcp.controllers import (
            ControllerPromptProvider,
            ControllerResourceProvider,
            ControllerToolProvider,
            MCPController,
        )

        instances: list[MCPController] = []
        for ctrl_class in self._controllers:
            try:
                instance: MCPController = await container.resolve(ctrl_class)
            except (UnresolvableDependencyError, LookupError) as exc:
                raise MCPInitializationError(
                    message=f"Failed to resolve MCP controller: {ctrl_class.__name__}"
                ) from exc
            instances.append(instance)
            logger.debug("mcp_controller_registered", controller=ctrl_class.__name__)

        container.singleton(ControllerToolProvider, ControllerToolProvider(instances))
        container.singleton(
            ControllerResourceProvider, ControllerResourceProvider(instances)
        )
        container.singleton(
            ControllerPromptProvider, ControllerPromptProvider(instances)
        )

    async def _boot_service_providers(self, container: BootContainerProtocol) -> None:
        """Resolve service classes and register a ServiceToolProvider."""
        from lexigram.ai.mcp.controllers import ServiceToolProvider

        instances: list[object] = []
        for svc_class in self._services:
            try:
                instance: object = await container.resolve(svc_class)
            except (UnresolvableDependencyError, LookupError) as exc:
                raise MCPInitializationError(
                    message=f"Failed to resolve MCP service: {svc_class.__name__}"
                ) from exc
            instances.append(instance)
            logger.debug("mcp_service_registered", service=svc_class.__name__)

        container.singleton(
            ServiceToolProvider,
            ServiceToolProvider.from_services(instances, self._include_methods),
        )

    async def _boot_skill_bridge(self, container: BootContainerProtocol) -> None:
        """Register SkillToolAdapter if lexigram-ai-skills is available.

        When ``SkillRegistryProtocol`` and ``SkillExecutorProtocol`` are
        registered in the container (by ``lexigram-ai-skills``), a
        :class:`~lexigram.ai.mcp.adapters.skill_adapter.SkillToolAdapter` is
        created and registered so that skills are exposed as MCP tools.
        """
        skill_registry = None
        skill_executor = None
        try:
            from lexigram.contracts.ai.skills import (
                SkillExecutorProtocol,
                SkillRegistryProtocol,
            )

            skill_registry = await container.resolve(SkillRegistryProtocol)
            skill_executor = await container.resolve(SkillExecutorProtocol)
        except (LookupError, RuntimeError, AttributeError, ImportError):
            logger.debug("mcp_skills_not_available")
            return

        from lexigram.ai.mcp.adapters.skill_adapter import SkillToolAdapter

        adapter = SkillToolAdapter(
            skill_registry=skill_registry,
            skill_executor=skill_executor,
        )
        container.singleton(SkillToolAdapter, adapter)
        logger.info("mcp_skill_bridge_registered")

    async def _boot_connectors(self, container: BootContainerProtocol) -> None:
        """Instantiate and register built-in connectors from ``MCPConfig.connectors``.

        Each connector that has sufficient configuration is instantiated and
        collected into :class:`~lexigram.ai.mcp.controllers._ConnectorToolBundle`
        and :class:`~lexigram.ai.mcp.controllers._ConnectorResourceBundle`
        sentinel types.  :meth:`_boot_handlers` then picks them up and merges
        them with the controller/service providers.
        """
        from lexigram.ai.mcp.connectors import (
            FilesystemConnector,
            GitHubConnector,
            GoogleDriveConnector,
            SlackConnector,
            SQLConnector,
            WebFetchConnector,
            WebSearchConnector,
        )
        from lexigram.ai.mcp.controllers import (
            _CombinedResourceProvider,
            _CombinedToolProvider,
        )

        cfg = self._config.connectors
        connectors: list[object] = []

        if cfg.filesystem.root_dir:
            connectors.append(
                FilesystemConnector(
                    root_dir=cfg.filesystem.root_dir,
                    read_only=cfg.filesystem.read_only,
                )
            )
            logger.info("mcp_connector_registered", connector="filesystem")

        if cfg.github.token:
            connectors.append(GitHubConnector(token=cfg.github.token))
            logger.info("mcp_connector_registered", connector="github")

        if cfg.web_fetch.enabled:
            connectors.append(
                WebFetchConnector(
                    max_content_bytes=cfg.web_fetch.max_content_bytes,
                )
            )
            logger.info("mcp_connector_registered", connector="web_fetch")

        if cfg.web_search.api_key:
            connectors.append(
                WebSearchConnector(
                    provider=cfg.web_search.provider,
                    api_key=cfg.web_search.api_key,
                    max_results=cfg.web_search.max_results,
                )
            )
            logger.info("mcp_connector_registered", connector="web_search")

        if cfg.slack.bot_token:
            connectors.append(
                SlackConnector(
                    bot_token=cfg.slack.bot_token,
                    max_messages=cfg.slack.max_messages,
                )
            )
            logger.info("mcp_connector_registered", connector="slack")

        if cfg.google_drive.service_account_json:
            connectors.append(
                GoogleDriveConnector(
                    service_account_json=cfg.google_drive.service_account_json,
                    impersonated_email=cfg.google_drive.impersonated_email,
                )
            )
            logger.info("mcp_connector_registered", connector="google_drive")

        if cfg.sql.dsn:
            try:
                from lexigram.contracts.data import DatabaseProviderProtocol

                db_provider = await container.resolve_optional(DatabaseProviderProtocol)
                if db_provider is not None:
                    connectors.append(
                        SQLConnector(
                            db=db_provider,
                            allowed_tables=cfg.sql.allowed_tables,
                            read_only=cfg.sql.read_only,
                        )
                    )
                    logger.info("mcp_connector_registered", connector="sql")
            except (ImportError, AttributeError, LookupError):
                logger.debug("mcp_sql_connector_skipped_no_db_provider")

        if not connectors:
            return

        tool_bundle = _CombinedToolProvider(connectors)
        resource_bundle = _CombinedResourceProvider(connectors)
        container.singleton(_ConnectorToolBundle, tool_bundle)
        container.singleton(_ConnectorResourceBundle, resource_bundle)

    async def _boot_handlers(self, container: BootContainerProtocol) -> None:
        """Register MCP handlers, wiring in controller providers when available.

        When ``MCPModule(controllers=[...])`` has already registered
        ``ControllerToolProvider`` / ``ControllerResourceProvider`` /
        ``ControllerPromptProvider`` in the container, those are passed to the
        handlers so that ``@tool``/``@resource``/``@prompt`` decorated methods
        are automatically exposed.  Falls back to empty (no-op) handlers when
        no controllers are configured.
        """
        from lexigram.ai.mcp.controllers import (
            ControllerPromptProvider,
            ControllerResourceProvider,
            ControllerToolProvider,
        )

        tool_provider: Any | None = await container.resolve_optional(
            ControllerToolProvider
        )
        resource_provider: Any | None = await container.resolve_optional(
            ControllerResourceProvider
        )
        prompt_provider: Any | None = await container.resolve_optional(
            ControllerPromptProvider
        )

        # Merge service tools with controller tools when both exist
        service_tool_provider = None
        try:
            from lexigram.ai.mcp.controllers import ServiceToolProvider

            service_tool_provider = await container.resolve_optional(
                ServiceToolProvider
            )
        except (ImportError, AttributeError):
            pass

        if tool_provider is not None and service_tool_provider is not None:
            from lexigram.ai.mcp.controllers import _CombinedToolProvider

            tool_provider = _CombinedToolProvider(
                [tool_provider, service_tool_provider]
            )
        elif service_tool_provider is not None:
            tool_provider = service_tool_provider

        # Merge built-in connector tools / resources when any connectors are configured
        connector_tool_bundle = await container.resolve_optional(_ConnectorToolBundle)
        connector_resource_bundle = await container.resolve_optional(
            _ConnectorResourceBundle
        )
        if connector_tool_bundle is not None:
            from lexigram.ai.mcp.controllers import _CombinedToolProvider

            tool_provider = _CombinedToolProvider(
                [p for p in [tool_provider, connector_tool_bundle] if p is not None]
            )
        if connector_resource_bundle is not None:
            from lexigram.ai.mcp.controllers import _CombinedResourceProvider

            resource_provider = _CombinedResourceProvider(
                [
                    p
                    for p in [resource_provider, connector_resource_bundle]
                    if p is not None
                ]
            )

        tool_handler = ToolHandler(tool_provider)
        resource_handler = ResourceHandler(resource_provider)
        prompt_handler = PromptHandler(prompt_provider)

        container.singleton(ToolHandler, tool_handler)
        container.singleton(ResourceHandler, resource_handler)
        container.singleton(PromptHandler, prompt_handler)

        # Optional: sampling handler (requires an LLM client in the container)
        try:
            from lexigram.contracts.ai.llm import LLMClientProtocol

            llm_client = await container.resolve_optional(LLMClientProtocol)
            if llm_client is not None:
                sampling_handler = SamplingHandler(llm=llm_client)
                container.singleton(SamplingHandler, sampling_handler)
                logger.info("mcp_sampling_handler_registered")
        except (ImportError, AttributeError):
            pass

        # Always register a logging handler
        logging_handler = LoggingHandler()
        container.singleton(LoggingHandler, logging_handler)

        # G41: Optional observability wrapping
        try:
            from lexigram.ai.mcp.server.observability import (
                ObservableResourceHandler,
                ObservableToolHandler,
            )
            from lexigram.contracts.observability.ai import AIMetricsProtocol

            metrics = await container.resolve_optional(AIMetricsProtocol)
            if metrics is not None:
                observable_tool = ObservableToolHandler(tool_handler, metrics)
                observable_resource = ObservableResourceHandler(
                    resource_handler, metrics
                )
                container.singleton(ToolHandler, observable_tool)
                container.singleton(ResourceHandler, observable_resource)
                logger.info("mcp_observability_wrapping_registered")
        except (ImportError, AttributeError):
            pass

        self._handlers_registered = True

    async def _boot_server(self, container: BootContainerProtocol) -> None:
        """Register MCP server."""
        tool_handler = await container.resolve(ToolHandler)
        resource_handler = await container.resolve(ResourceHandler)
        prompt_handler = await container.resolve(PromptHandler)
        sampling_handler = await container.resolve_optional(SamplingHandler)
        logging_handler = await container.resolve_optional(LoggingHandler)

        server = MCPServer(
            name=self._config.server_name,
            version=self._config.server_version,
            tool_handler=tool_handler,
            resource_handler=resource_handler,
            prompt_handler=prompt_handler,
            sampling_handler=sampling_handler,
            logging_handler=logging_handler,
        )

        registrar = cast("ContainerRegistrarProtocol", container)
        registrar.singleton(MCPServer, server)

    def _boot_transports(self, container: ContainerRegistrarProtocol) -> None:
        """Register MCP transport singletons."""
        stdio_transport = StdioTransport()
        sse_transport = SSETransport()

        container.singleton(StdioTransport, stdio_transport)
        container.singleton(SSETransport, sse_transport)
        self._managed_transports = [stdio_transport, sse_transport]

    async def shutdown(self) -> None:
        """Clean up MCP provider resources."""
        for transport in self._managed_transports:
            try:
                await transport.stop()
            except (RuntimeError, AttributeError, TypeError, OSError) as exc:
                logger.warning(
                    "mcp_transport_stop_failed",
                    transport=type(transport).__name__,
                    error=str(exc),
                )

        self._managed_transports.clear()

        if self._managed_client is not None:
            try:
                await self._managed_client.disconnect()
            except (
                RuntimeError,
                AttributeError,
                TypeError,
                OSError,
                ConnectionError,
                TimeoutError,
            ) as exc:
                logger.warning("mcp_client_disconnect_failed", error=str(exc))
            self._managed_client = None

        logger.info("mcp_provider_shutdown_complete")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return a health check result for this provider.

        Args:
            timeout: Maximum seconds to wait for health response.

        Returns:
            A :class:`~lexigram.contracts.core.health.HealthCheckResult`
            reflecting the current MCP provider state.
        """
        if self._managed_client is not None:
            is_connected = getattr(self._managed_client, "is_connected", None)
            if (callable(is_connected) and not is_connected()) or (
                isinstance(is_connected, bool) and not is_connected
            ):
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.DEGRADED,
                    details={"reason": "MCP client disconnected"},
                )
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )

    async def _boot_client(self, container: BootContainerProtocol) -> None:
        """Register MCPClient if client configuration is present."""
        from lexigram.ai.mcp.client.core import (
            MCPClient,
            SSEClientTransport,
            StdioClientTransport,
        )

        self._managed_client = None

        if self._config.client_stdio_command:
            stdio_client_transport = StdioClientTransport(
                self._config.client_stdio_command,
                startup_timeout=self._config.request_timeout,
            )
            client = MCPClient(
                stdio_client_transport, request_timeout=self._config.request_timeout
            )
            registrar = cast("ContainerRegistrarProtocol", container)
            registrar.singleton(MCPClient, client)
            self._managed_client = client
            logger.info(
                "mcp_client_registered",
                mode="stdio",
                command=self._config.client_stdio_command[0],
            )
        elif self._config.client_url:
            sse_client_transport = SSEClientTransport(
                self._config.client_url,
                request_timeout=self._config.request_timeout,
            )
            client = MCPClient(
                sse_client_transport, request_timeout=self._config.request_timeout
            )
            registrar = cast("ContainerRegistrarProtocol", container)
            registrar.singleton(MCPClient, client)
            self._managed_client = client
            logger.info(
                "mcp_client_registered",
                mode="sse",
                url=self._config.client_url,
            )


__all__ = ["MCPProvider"]
