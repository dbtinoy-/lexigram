"""RelayProvider — registers the relay registry and conversion engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.relay.engine import RelayConverterEngine
from lexigram.ai.relay.registry import RelayConverterRegistry
from lexigram.contracts.ai.relay.protocols import (
    RelayConverterProtocol,
    RelayRegistryProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


class RelayProvider(Provider):
    """Registers the caller-owned relay registry and the public engine.

    The provider binds a default :class:`RelayConverterRegistry` when the
    caller did not already register their own ``RelayRegistryProtocol``;
    it never overrides an existing caller-owned registry.  The engine is
    registered as its class so the container constructs it against
    whichever registry binding wins.

    Registers:
    - ``RelayRegistryProtocol`` — the default registry (only when absent)
    - ``RelayConverterProtocol`` — the public conversion engine

    The provider requires no LLM API credentials and never creates an
    HTTP client.
    """

    name = "ai-relay"

    # TODO(config): declare ``config_key = "ai_relay"`` /
    # ``config_model = RelayConfig`` once relay-level knobs exist in
    # application.yaml (e.g. default conversion caps, protocol defaults).
    # The conversion engine is currently side-effect free and stateless, so
    # there is nothing to inject yet.
    priority = ProviderPriority.DOMAIN

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the relay registry and engine."""
        if not container.has(RelayRegistryProtocol):
            container.singleton(
                RelayRegistryProtocol,
                RelayConverterRegistry.with_defaults(),
            )
        container.singleton(RelayConverterProtocol, RelayConverterEngine)
        logger.info("relay_provider_registered")

    async def boot(self, container: BootContainerProtocol) -> None:
        """No-op boot; the engine needs no runtime wiring."""
        logger.info("relay_provider_booted")

    async def shutdown(self) -> None:
        """No-op shutdown."""
        logger.info("relay_provider_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report the relay engine as healthy.

        Args:
            timeout: Ignored; the engine performs no I/O.

        Returns:
            A healthy check result.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
        )
