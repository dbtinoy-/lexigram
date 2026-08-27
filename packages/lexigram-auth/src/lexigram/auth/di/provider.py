"""DI provider for lexigram-auth.

This provider wires the auth subsystem with ClockProtocol, IdGeneratorProtocol,
TracerProtocol, and MetricsCollectorProtocol for testability and hardening.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.auth.authn.password_hasher import Argon2idKeyDerivation
from lexigram.auth.config import AuthConfig
from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.core.health import HealthCheckCategory
from lexigram.contracts.security.protocols import KeyDerivationProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

__all__ = ["AuthProvider"]


class AuthProvider(Provider):
    """Authentication provider for Lexigram Framework.

    This provider wires:
    - ClockProtocol for token/session timestamps
    - IdGeneratorProtocol for session/token IDs
    - TracerProtocol for observability
    - MetricsCollectorProtocol for metrics
    - KeyDerivationProtocol (Argon2id) for key derivation
    """

    name = "auth"
    priority = ProviderPriority.SECURITY

    config_key: str | None = "auth"
    config_model: type | None = AuthConfig

    def __init__(self, config: AuthConfig | None = None) -> None:
        super().__init__()
        self._config = config

    @classmethod
    def from_config(cls, config: AuthConfig, **context: Any) -> AuthProvider:
        return cls(config=config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register auth services with the DI container."""
        if self._config is None:
            self._config = AuthConfig()
        container.singleton(AuthConfig, instance=self._config)

        container.singleton(
            KeyDerivationProtocol,
            factory=lambda _: Argon2idKeyDerivation(config=self._config.password),
        )

        if self._config.relay_verification:
            from lexigram.auth.authn.apikeys import APIKeyManager
            from lexigram.auth.authn.relay import RelayApiKeyVerifier
            from lexigram.contracts.ai.relay import RelayAuthVerifierProtocol
            from lexigram.contracts.auth import APIKeyRepositoryProtocol

            if not container.has(APIKeyRepositoryProtocol):
                logger.warning(
                    "relay_verifier_skipped",
                    reason="APIKeyRepositoryProtocol not bound",
                )
                return
            container.singleton(
                RelayAuthVerifierProtocol,
                factory=lambda c: RelayApiKeyVerifier(
                    manager=APIKeyManager(repo=c.resolve(APIKeyRepositoryProtocol))
                ),
            )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot the auth provider."""

    async def shutdown(self) -> None:
        """Shutdown the auth provider."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return health status of the auth provider."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
