from __future__ import annotations

from lexigram.config.main import LexigramConfig
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider, ProviderPriority


class LoggingProvider(Provider):
    """Structured logging factory and helpers DI provider."""

    name = "logging"
    priority = ProviderPriority.INFRASTRUCTURE
    dependencies = ("config",)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register logging services."""
        from lexigram.contracts.core.logging import RedactorProtocol
        from lexigram.logging import (
            LoggerFactoryImpl,
            LoggerFactoryProtocol,
            get_logger,
        )
        from lexigram.logging import LoggerProtocol as Logger
        from lexigram.logging.redaction import DelegatingRedactor

        logger_factory = LoggerFactoryImpl()
        container.singleton(LoggerFactoryProtocol, logger_factory)
        container.singleton(Logger, get_logger("lexigram"))
        container.singleton(RedactorProtocol, DelegatingRedactor())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Apply logging configuration from LexigramConfig."""
        from lexigram.logging.configurator import apply_config

        config = await container.resolve(LexigramConfig)
        apply_config(config.logging, service_name=getattr(config, "app_name", None))

    async def shutdown(self) -> None:
        """No resources to release for the logging module."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process only, no external backend).

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to check.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )


__all__ = ["LoggingProvider"]
