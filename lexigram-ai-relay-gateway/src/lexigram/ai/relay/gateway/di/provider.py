"""RelayGatewayProvider — registers the relay gateway behind its contract.

The provider composes the gateway service from caller-owned dependencies.
Configuration, the conversion engine, and the HTTP client are injected at
construction; the registry, codec, upstream adapter, and service are built
and registered against the container.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.auto_test import RelayChannelAutoTester
from lexigram.ai.relay.gateway.operations.controls import (
    InMemoryRelayPolicyStore,
    RelayControlsService,
)
from lexigram.ai.relay.gateway.operations.health import (
    RelayChannelCheckerProtocol,
    RelayHealthService,
)
from lexigram.ai.relay.gateway.operations.metrics import (
    RelayMetricsService,
    RelayRouteEventSourceProtocol,
)
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.passthrough import PassthroughService
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import (
    AIAuditStoreProtocol,
    RelayBillingProtocol,
)
from lexigram.contracts.ai.relay import (
    MediaResolverProtocol,
    RelayConverterProtocol,
    RelayGatewayProtocol,
    RelayPolicyStoreProtocol,
    RelayRegistryProtocol,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.web import HTTPClientProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class RelayGatewayProvider(Provider):
    """Provider registering the relay gateway behind ``RelayGatewayProtocol``.

    The caller owns the static configuration, the conversion engine, and
    the HTTP client; the provider wires them into a ready-to-serve
    :class:`RelayGatewayService`. Optional governance hooks (authorizer,
    media resolver, billing) are forwarded to the service as-is.

    Configuration is explicit-only (a frozen channel/conversion table);
    the gateway is not bound to a ``LexigramConfig`` section, so this
    provider declares no ``config_key``/``config_model`` attributes.

    Registers:
    - ``RelayGatewayConfig`` — the injected configuration (always)
    - ``RelayChannelRegistry`` — a registry built from the configuration
    - ``RelayPolicyStoreProtocol`` — the runtime policy backend (always)
    - ``RelayHealthService`` — channel health probing (always)
    - ``RelayMetricsService`` — route metrics aggregation (always)
    - ``RelayControlsService`` — permissioned control mutations (always)
    - ``RelayChannelAutoTester`` — background channel auto-tester (only
      when ``auto_test_channels`` is enabled in the configuration)
    - ``RelayGatewayProtocol`` — the gateway service (only when both the
      converter and an HTTP client are available)
    - ``PassthroughService`` — passthrough endpoint dispatch (same
      availability as the gateway service)

    Args:
        config: Gateway channel table and conversion metadata. Defaults
            to an empty configuration when omitted.
        converter: Conversion engine implementing
            ``RelayConverterProtocol``. When ``None`` a startup
            diagnostic is logged and the gateway binding is skipped.
        http_client: HTTP client driving the upstream adapter. When
            ``None`` a startup diagnostic is logged and the gateway
            binding is skipped.
        authorizer: Optional authorizer enforced before dispatch.
        media_resolver: Optional media resolver placed on the conversion
            context.
        billing: Optional billing lifecycle; when ``None`` the gateway
            runs without admission control or settlement.
        converter_registry: Converter registry backing health and metrics
            diagnostics and route quality. Optional; when ``None`` the
            diagnostic surfaces are unavailable (``DEPENDENCY_UNAVAILABLE``).
        channel_checker: Optional channel checker driving per-channel
            probes; when ``None`` the health service reports unchecked
            channels.
        metrics_events: Optional route event source feeding metrics
            aggregation; when ``None`` the metrics surface is unavailable.
        policy_store: Optional runtime policy backend. ``None`` installs
            an in-process ``InMemoryRelayPolicyStore`` seeded from the
            configuration.
        audit: Optional audit backend for control mutations. ``None``
            disables audit emission.
    """

    name = "ai-relay-gateway"
    priority = ProviderPriority.DOMAIN

    def __init__(
        self,
        *,
        config: RelayGatewayConfig | None = None,
        converter: RelayConverterProtocol | None = None,
        http_client: HTTPClientProtocol | None = None,
        authorizer: AuthorizerProtocol | None = None,
        media_resolver: MediaResolverProtocol | None = None,
        billing: RelayBillingProtocol | None = None,
        converter_registry: RelayRegistryProtocol | None = None,
        channel_checker: RelayChannelCheckerProtocol | None = None,
        metrics_events: RelayRouteEventSourceProtocol | None = None,
        policy_store: RelayPolicyStoreProtocol | None = None,
        audit: AIAuditStoreProtocol | None = None,
    ) -> None:
        super().__init__()
        self._config = config if config is not None else RelayGatewayConfig()
        self._converter = converter
        self._http_client = http_client
        self._authorizer = authorizer
        self._media_resolver = media_resolver
        self._billing = billing
        self._converter_registry = converter_registry
        self._channel_checker = channel_checker
        self._metrics_events = metrics_events
        self._policy_store = (
            policy_store
            if policy_store is not None
            else InMemoryRelayPolicyStore.with_defaults(self._config)
        )
        self._audit = audit
        self._auto_tester: RelayChannelAutoTester | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the gateway configuration, registry, and service.

        The configuration and registry are always bound. The gateway
        service itself is only bound when the converter and HTTP client
        are both present; otherwise a startup diagnostic is logged so the
        missing dependency is discoverable.

        Args:
            container: The container registrar to bind into.
        """
        registry = RelayChannelRegistry(self._config)
        streams = RelayStreamRegistry()
        container.singleton(RelayGatewayConfig, self._config)
        container.singleton(RelayChannelRegistry, registry)
        container.singleton(RelayStreamRegistry, streams)
        container.singleton(RelayPolicyStoreProtocol, self._policy_store)
        health_service = RelayHealthService(
            registry=registry,
            checker=self._channel_checker,
            converter=self._converter_registry,
            policy=self._policy_store,
        )
        container.singleton(RelayHealthService, health_service)
        if self._config.auto_test_channels:
            self._auto_tester = RelayChannelAutoTester(
                health=health_service,
                registry=registry,
                interval_seconds=self._config.auto_test_interval_seconds,
            )
            container.singleton(RelayChannelAutoTester, self._auto_tester)
        metrics_service = RelayMetricsService(
            events=self._metrics_events,
            converter=self._converter_registry,
        )
        container.singleton(RelayMetricsService, metrics_service)
        controls_service = RelayControlsService(
            registry=registry,
            store=self._policy_store,
            authorizer=self._authorizer,
            audit=self._audit,
            streams=streams,
        )
        container.singleton(RelayControlsService, controls_service)
        if self._converter is None:
            logger.warning(
                "relay_gateway_missing_dependency",
                missing="RelayConverterProtocol",
            )
            return
        if self._http_client is None:
            logger.warning(
                "relay_gateway_missing_dependency",
                missing="HTTPClientProtocol",
            )
            return
        service = RelayGatewayService(
            converter=self._converter,
            codec=RelayPayloadCodec(),
            registry=registry,
            upstream=HTTPUpstreamAdapter(self._http_client),
            config=self._config,
            authorizer=self._authorizer,
            billing=self._billing,
            media_resolver=self._media_resolver,
            streams=streams,
        )
        container.singleton(RelayGatewayProtocol, service)
        passthrough_service = PassthroughService(
            registry=registry,
            upstream=HTTPUpstreamAdapter(self._http_client),
            config=self._config,
            authorizer=self._authorizer,
            billing=self._billing,
        )
        container.singleton(PassthroughService, passthrough_service)
        logger.info("relay_gateway_provider_registered")

    async def boot(self, container: BootContainerProtocol) -> None:
        """Reconcile persisted policy drains into runtime selection.

        Channels the policy store marks disabled (while the static
        configuration still enables them) are drained in the runtime
        registry so dispatch honors the persisted policy from the first
        request onward. When auto-testing is enabled, the background
        sweep is started after reconciliation.

        Args:
            container: The booted container used to resolve the policy
                store and channel registry.
        """
        registry = await container.resolve(RelayChannelRegistry)
        policy = await container.resolve(RelayPolicyStoreProtocol)
        snapshot = await policy.load()
        for channel in self._config.channels:
            if channel.enabled and not snapshot.enabled_channels.get(
                channel.name, True
            ):
                registry.set_runtime_enabled(channel.name, False)
        if self._auto_tester is not None:
            await self._auto_tester.start()
        logger.info("relay_gateway_provider_booted")

    async def shutdown(self) -> None:
        """Stop the background auto-tester, if one was started."""
        if self._auto_tester is not None:
            await self._auto_tester.stop()


__all__ = ["RelayGatewayProvider"]
