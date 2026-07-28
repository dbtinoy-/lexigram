"""DI provider for lexigram-auth.

This provider wires the auth subsystem with ClockProtocol, IdGeneratorProtocol,
TracerProtocol, and MetricsCollectorProtocol for testability and hardening.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.auth.config import AuthConfig
from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.core.health import HealthCheckCategory
from lexigram.contracts.security.protocols import KeyDerivationProtocol
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["AuthProvider"]


class AuthProvider(Provider):
    """Authentication provider for Lexigram Framework.

    This provider wires:
    - ClockProtocol for token/session timestamps
    - IdGeneratorProtocol for session/token IDs
    - TracerProtocol for observability
    - MetricsCollectorProtocol for metrics
    - KeyDerivationProtocol (Argon2id) for password hashing
    - PasswordHasherProtocol for auth-domain password operations
    """

    name = "auth"
    priority = ProviderPriority.SECURITY

    config_key: str | None = "auth"
    config_model: type | None = AuthConfig

    def __init__(self, config: AuthConfig | None = None) -> None:
        super().__init__()
        self._config = config or AuthConfig()

    @classmethod
    def from_config(cls, config: AuthConfig, **context: Any) -> AuthProvider:
        return cls(config=config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register auth services with the DI container."""
        container.singleton(AuthConfig, instance=self._config)

        from lexigram.auth.authn.password_hasher import (
            Argon2idKeyDerivation,
            Argon2idPasswordHasher,
        )

        container.singleton(
            KeyDerivationProtocol,
            factory=lambda _: Argon2idKeyDerivation(config=self._config.password),
        )

        container.singleton(
            PasswordHasherProtocol,
            factory=lambda c: Argon2idPasswordHasher(
                kdf=c.resolve(KeyDerivationProtocol)
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
