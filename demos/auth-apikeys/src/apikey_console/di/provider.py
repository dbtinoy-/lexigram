"""DI wiring for the API-keys console demo."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from apikey_console.controllers.api import KeysApiController
from apikey_console.repository.keys_repository import InMemoryAPIKeyRepository
from apikey_console.repository.session_repository import InMemorySessionRepository
from apikey_console.services.seed import DEMO_EMAIL, DEMO_PASSWORD, DemoSeedService
from apikey_console.ui.pages import PagesController
from lexigram.auth.authn.apikeys import APIKeyManager
from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth import APIKeyRepositoryProtocol, AuthenticatedUserProtocol
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

logger = get_logger(__name__)


def build_auth_config() -> AuthConfig:
    """Offline demo config with an explicit dev secret."""
    secret = "apikeys-console-demo-secret-key-01234567"
    return AuthConfig(
        secret_key=secret,
        token=JWTConfig(secret_key=secret),
    )


class ApiKeysProvider(Provider):
    """Seed the demo user and wire key management + machine auth."""

    name = "apikeys-console"

    def __init__(self) -> None:
        super().__init__()
        self._session_repository = InMemorySessionRepository()
        self._keys_repository = InMemoryAPIKeyRepository()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness."""
        return HealthCheckResult(component=self.name)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind builders; collaborators resolve lazily via the container."""
        container.singleton(
            InMemorySessionRepository, instance=self._session_repository
        )
        container.singleton(
            SessionRepositoryProtocol, instance=self._session_repository
        )
        container.singleton(InMemoryAPIKeyRepository, instance=self._keys_repository)
        container.singleton(APIKeyRepositoryProtocol, instance=self._keys_repository)
        container.singleton(UserService, factory=self._build_user_service)
        container.singleton(SessionCookieBackend, factory=self._build_session_backend)
        container.singleton(APIKeyManager, factory=self._build_key_manager)
        container.singleton(KeysApiController, factory=self._build_api)
        container.singleton(PagesController, instance=PagesController())
        container.singleton(DemoSeedService, factory=self._build_seed_service)

    async def _build_user_service(
        self, resolver: ContainerResolverProtocol
    ) -> UserService:
        """Build UserService on the SAME policy/store AuthenticationService
        holds, so seeded users are visible to login."""
        authentication = await resolver.resolve(AuthenticationService)
        return UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_session_backend(
        self, resolver: ContainerResolverProtocol
    ) -> SessionCookieBackend:
        user_service = await resolver.resolve(UserService)
        repository = await resolver.resolve(SessionRepositoryProtocol)
        return SessionCookieBackend(
            session_repository=repository,
            user_fetcher=cast(
                "Callable[[str], Awaitable[AuthenticatedUserProtocol | None]]",
                user_service.get_user,
            ),
            secure=False,  # local demo runs plain http
        )

    async def _build_key_manager(
        self, resolver: ContainerResolverProtocol
    ) -> APIKeyManager:
        repository = await resolver.resolve(APIKeyRepositoryProtocol)
        return APIKeyManager(repo=repository)

    async def _build_api(
        self, resolver: ContainerResolverProtocol
    ) -> KeysApiController:
        authentication = await resolver.resolve(AuthenticationService)
        cookies = await resolver.resolve(SessionCookieBackend)
        manager = await resolver.resolve(APIKeyManager)
        return KeysApiController(
            authentication=authentication, cookies=cookies, manager=manager
        )

    async def _build_seed_service(
        self, resolver: ContainerResolverProtocol
    ) -> DemoSeedService:
        return DemoSeedService(users=await resolver.resolve(UserService))

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Seed the demo account; everything else wires lazily."""
        seeder = await container.resolve(DemoSeedService)
        await seeder.run()


__all__ = ["DEMO_EMAIL", "DEMO_PASSWORD", "ApiKeysProvider"]
