"""DI wiring for the API-keys console demo."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from apikey_console.controllers.api import KeysApiController
from apikey_console.repository.keys_repository import InMemoryAPIKeyRepository
from apikey_console.repository.session_repository import InMemorySessionRepository
from apikey_console.services.seed import DEMO_EMAIL, DEMO_PASSWORD, DemoSeedService
from apikey_console.ui.pages import PagesController
from lexigram.auth.authn.apikeys import APIKeyManager
from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth import APIKeyRepositoryProtocol, AuthenticatedUserProtocol
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

logger = get_logger(__name__)


class ApiKeysProvider(Provider):
    """Seed the demo user and wire key management + machine auth."""

    name = "apikeys-console"

    def __init__(self) -> None:
        super().__init__()
        self._session_repository = InMemorySessionRepository()
        self._keys_repository = InMemoryAPIKeyRepository()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the key-management stack."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; cross-service wiring happens in :meth:`boot`."""
        container.singleton(
            InMemorySessionRepository, instance=self._session_repository
        )
        container.singleton(
            SessionRepositoryProtocol, instance=self._session_repository
        )
        container.singleton(InMemoryAPIKeyRepository, instance=self._keys_repository)
        container.singleton(APIKeyRepositoryProtocol, instance=self._keys_repository)
        container.singleton(UserService, UserService)
        container.singleton(SessionCookieBackend, SessionCookieBackend)
        container.singleton(APIKeyManager, APIKeyManager)
        container.singleton(KeysApiController, KeysApiController)
        container.singleton(PagesController, PagesController)
        container.singleton(DemoSeedService, DemoSeedService)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve the auth stack, bind concrete instances, seed the demo user.

        ``UserService`` is built on the SAME policy/store that
        :class:`AuthenticationService` holds so seeded users are visible to
        login.
        """
        from typing import cast

        authentication = await container.resolve(AuthenticationService)

        user_service = UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )
        container.bind(UserService, user_service)

        container.bind(
            SessionCookieBackend,
            SessionCookieBackend(
                session_repository=self._session_repository,
                user_fetcher=cast(
                    "Callable[[str], Awaitable[AuthenticatedUserProtocol | None]]",
                    user_service.get_user,
                ),
                secure=False,  # local demo runs plain http
            ),
        )
        container.bind(
            APIKeyManager,
            APIKeyManager(repo=self._keys_repository),
        )
        container.bind(
            DemoSeedService,
            DemoSeedService(users=user_service),
        )
        seeder = await container.resolve(DemoSeedService)
        await seeder.run()

        container.bind(
            KeysApiController,
            KeysApiController(
                authentication=authentication,
                cookies=await container.resolve(SessionCookieBackend),
                manager=await container.resolve(APIKeyManager),
            ),
        )


__all__ = ["DEMO_EMAIL", "DEMO_PASSWORD", "ApiKeysProvider"]
