"""CLI Provider for Lexigram Framework.

This module provides CLI-specific functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.cli.constants import __version__
from lexigram.cli.di.sub_providers.contributor import CliContributorSubProvider
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.cli.config import CLIConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

_logger = get_logger(__name__)


class CLIProvider(Provider):
    """Provider for CLI-specific configuration and command registration.

    Registers CLI configuration and any CLI-specific singletons into the
    DI container.  Boot is intentionally lightweight — the CLI process does
    not require long-lived background resources.

    The ``CliContributorSubProvider`` is composed here so that the full
    contribution system (contributor registry, generator registry, and
    assembler) is wired during the standard DI boot sequence.
    """

    name = "cli"
    priority = ProviderPriority.APPLICATION

    def __init__(self, config: CLIConfig | None = None) -> None:
        """Initialize CLI Provider.

        Args:
            config: CLI configuration.  When ``None``, the provider registers
                with default settings and defers configuration to the
                environment or a separate config provider.
        """
        super().__init__()
        self._cli_config = config
        self._contributor_sub_provider = CliContributorSubProvider()

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind CLI configuration and contribution-system singletons into the container."""
        if self._cli_config is not None:
            from lexigram.cli.config import CLIConfig

            container.singleton(CLIConfig, self._cli_config)

        await self._contributor_sub_provider.register(container)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot the CLI provider and wire the contribution system.

        Delegates to ``CliContributorSubProvider.boot()`` to wire the core
        contributor into the registry.  No long-lived resources are acquired;
        the CLI process completes within a single invocation.
        """
        await self._contributor_sub_provider.boot(container)
        _logger.info("cli_provider_boot")

    async def shutdown(self) -> None:
        """Shut down the CLI provider and release any held resources."""
        _logger.info("cli_provider_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report health of the CLI provider.

        The CLI provider is stateless — it holds no external connections —
        so this always returns healthy.

        Args:
            timeout: Unused; included for interface consistency.

        Returns:
            :attr:`~lexigram.contracts.core.health.HealthStatus.HEALTHY` result.
        """
        return HealthCheckResult(
            component="cli",
            status=HealthStatus.HEALTHY,
            message="CLI provider operational - no external dependencies",
        )

    def get_version(self) -> str:
        """Get CLI version."""
        return __version__


__all__ = ["CLIProvider"]
