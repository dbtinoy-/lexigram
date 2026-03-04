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
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.governance import RelayBillingProtocol
from lexigram.contracts.ai.relay import (
    MediaResolverProtocol,
    RelayConverterProtocol,
    RelayGatewayProtocol,
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

    Registers:
    - ``RelayGatewayConfig`` — the injected configuration (always)
    - ``RelayChannelRegistry`` — a registry built from the configuration
    - ``RelayGatewayProtocol`` — the gateway service (only when both the
      converter and an HTTP client are available)

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
    ) -> None:
        super().__init__()
        self._config = config if config is not None else RelayGatewayConfig()
        self._converter = converter
        self._http_client = http_client
        self._authorizer = authorizer
        self._media_resolver = media_resolver
        self._billing = billing

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
        container.singleton(RelayGatewayConfig, self._config)
        container.singleton(RelayChannelRegistry, registry)
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
        )
        container.singleton(RelayGatewayProtocol, service)
        logger.info("relay_gateway_provider_registered")

    async def boot(self, container: BootContainerProtocol) -> None:
        """No-op boot; the gateway needs no runtime wiring."""

    async def shutdown(self) -> None:
        """No-op shutdown; the upstream adapter has no lifecycle."""


__all__ = ["RelayGatewayProvider"]
