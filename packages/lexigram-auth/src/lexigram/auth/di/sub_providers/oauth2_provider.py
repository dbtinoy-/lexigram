# lexigram/auth/providers/oauth2_provider.py
"""OAuth2 provider - handles OAuth2/OIDC integration only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from lexigram.auth.authn.oauth2 import (
    OAuth2IdentityProvider as OAuth2IdentityProviderConfig,
)
from lexigram.auth.authn.oauth2 import OAuth2Manager
from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.di.decorators import inject
from lexigram.di.markers import Inject
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.auth.config import AuthConfig
    from lexigram.auth.storage.oauth_identity_store import OAuthIdentityStore
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


@inject
class OAuth2Provider(Provider):
    """OAuth2/OIDC integration ONLY."""

    def __init__(
        self,
        config: Annotated[AuthConfig, Inject] | None = None,
        oauth2_providers: dict[str, dict[str, str]] | None = None,
        oauth_identity_store: OAuthIdentityStore | None = None,
        http_client: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name="oauth2", priority=ProviderPriority.SECURITY)
        self.oauth2_providers = oauth2_providers or (
            config.oauth2_providers if config else {}
        )
        self.oauth_identity_store: OAuthIdentityStore | None = oauth_identity_store
        self.http_client = http_client

    @property
    def identity_resolver(self) -> OAuthIdentityStore | None:
        """Return the OAuth identity store for resolving external IDs to internal UUIDs.

        This property exposes the OAuthIdentityStore which implements
        IdentityResolverProtocol for resolving OAuth external IDs.
        """
        return self.oauth_identity_store

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register OAuth2 services with the container."""
        # Convert raw config dicts to OAuth2IdentityProviderConfig instances
        resolved_providers: dict[str, OAuth2IdentityProviderConfig] = {
            provider_name: OAuth2IdentityProviderConfig(
                name=provider_name,
                client_id=cfg.get("client_id", ""),
                client_secret=cfg.get("client_secret", ""),
                authorize_url=cfg.get("authorize_url", ""),
                access_token_url=cfg.get("access_token_url", ""),
                userinfo_url=cfg.get("userinfo_url", ""),
                scope=cfg.get("scope", "openid email profile"),
                redirect_uri=cfg.get("redirect_uri"),
            )
            for provider_name, cfg in self.oauth2_providers.items()
        }

        # OAuth2 manager
        oauth2_manager = OAuth2Manager(
            providers=resolved_providers,
            http_client=self.http_client,
        )
        container.singleton(OAuth2Manager, lambda: oauth2_manager)

        # Register OAuthIdentityStore for identity resolution
        # This enables resolving user IDs from OAuth external IDs
        from lexigram.auth.storage.oauth_identity_store import (
            OAuthIdentityStore,
        )

        container.singleton(OAuthIdentityStore, lambda: self.oauth_identity_store)

        # Register individual OAuth2 providers
        for name, cfg in self.oauth2_providers.items():
            provider = OAuth2IdentityProviderConfig(
                name=name,
                client_id=cfg.get("client_id", ""),
                client_secret=cfg.get("client_secret", ""),
                authorize_url=cfg.get("authorize_url", ""),
                access_token_url=cfg.get("access_token_url", ""),
                userinfo_url=cfg.get("userinfo_url", ""),
                scope=cfg.get("scope", "openid email profile"),
                redirect_uri=cfg.get("redirect_uri"),
                require_pkce=cfg.get("require_pkce", "true").lower() == "true",
            )
            container.singleton(f"oauth2.{name}", lambda p=provider: p)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize OAuth2 provider."""
        logger.info("OAuth2Provider started")

    async def shutdown(self) -> None:
        """Shutdown OAuth2 provider."""
        logger.info("OAuth2Provider shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check OAuth2 provider health."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={
                "service": "oauth2",
                "providers_count": len(self.oauth2_providers),
                "identity_store_type": type(self.oauth_identity_store).__name__,
            },
        )


__all__ = [
    "OAuth2Provider",
    "logger",
]
