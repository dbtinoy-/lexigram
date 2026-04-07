# lexigram/auth/providers/authorization_provider.py
"""Authorization provider - handles role-based access control and permissions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from lexigram.auth.authz.service import AuthorizationService
from lexigram.contracts import (
    AuthorizerProtocol,
    HealthCheckResult,
    HealthStatus,
    ProviderPriority,
)
from lexigram.di.decorators import inject
from lexigram.di.markers import Inject
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.auth.config import AuthConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


@inject
class AuthorizationProvider(Provider):
    """Role-based access control and permission management."""

    def __init__(
        self,
        config: Annotated[AuthConfig, Inject] | None = None,
        initial_roles: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="authorization", priority=ProviderPriority.SECURITY)
        self._config = config
        self.initial_roles = initial_roles or {}

    @property
    def auth_config(self) -> AuthConfig | None:
        return self._config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register authorization services with the container."""
        ttl = (
            getattr(self.auth_config.rbac, "permission_cache_ttl", 300.0)
            if self.auth_config and self.auth_config.rbac
            else 300.0
        )
        auth_service = AuthorizationService(permission_cache_ttl=ttl)

        if self.initial_roles:
            auth_service.set_roles(self.initial_roles)

        container.singleton(AuthorizerProtocol, lambda: auth_service)
        container.singleton(AuthorizationService, lambda: auth_service)

        logger.info(
            "AuthorizationProvider registered with %d initial roles",
            len(self.initial_roles),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize authorization provider."""
        logger.info("AuthorizationProvider started")

    async def shutdown(self) -> None:
        """Shutdown authorization provider."""
        logger.info("AuthorizationProvider shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check authorization provider health."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={
                "service": "authorization",
                "initial_roles_count": len(self.initial_roles),
            },
        )


__all__ = [
    "AuthorizationProvider",
    "logger",
]
