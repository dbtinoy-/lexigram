"""DI wiring for the auth web demo."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from auth_web.controllers.api import AuthApiController
from auth_web.repository import InMemorySessionRepository
from auth_web.services.password_change import PasswordChangeService
from auth_web.services.seed import DEMO_EMAIL, DEMO_PASSWORD, DemoSeedService
from auth_web.ui.pages import PagesController
from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth import AuthenticatedUserProtocol
from lexigram.contracts.auth.protocols import PasswordHasherProtocol
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider

DEMO_SECRET = "auth-web-demo-secret-key-0123456789abcdef"

__all__ = [
    "DEMO_EMAIL",
    "DEMO_PASSWORD",
    "AuthWebProvider",
    "build_auth_config",
]


def build_auth_config() -> AuthConfig:
    """Offline demo config: explicit dev secrets.

    Note:
        ``AuthConfig.users`` and ``AuthConfig.roles`` are inert today
        (nothing consumes them at boot), so the demo account is seeded via
        :class:`~auth_web.services.seed.DemoSeedService` in
        :meth:`AuthWebProvider.boot`.
    """
    return AuthConfig(
        secret_key=DEMO_SECRET,
        token=JWTConfig(secret_key=DEMO_SECRET),
    )


class AuthWebProvider(Provider):
    """Assemble the demo's session layer and register UI services.

    All boot-built collaborators are exposed as resolver-receiving async
    factories: the container invokes them lazily (and awaits them), so the
    provider holds no state and needs no None-guards.
    """

    name = "auth-web"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness."""
        return HealthCheckResult(component=self.name)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind pure instances now; collaborators build lazily post-boot."""
        repository = InMemorySessionRepository()
        container.singleton(InMemorySessionRepository, instance=repository)
        container.singleton(SessionRepositoryProtocol, instance=repository)
        container.singleton(UserService, factory=self._build_user_service)
        container.singleton(SessionCookieBackend, factory=self._build_backend)
        container.singleton(PasswordChangeService, factory=self._build_password_changes)
        container.singleton(AuthApiController, factory=self._build_api)
        container.singleton(PagesController, instance=PagesController())
        container.singleton(DemoSeedService, factory=self._build_seed_service)

    async def _build_user_service(
        self, resolver: ContainerResolverProtocol
    ) -> UserService:
        authentication = await resolver.resolve(AuthenticationService)
        # UserService ships unregistered: build it on the SAME policy/user
        # store AuthenticationService holds so password changes are visible
        # to login.
        # TODO(framework): export UserService (or its dep keys) from
        # lexigram-auth so this attribute-fishing disappears.
        return UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_backend(
        self, resolver: ContainerResolverProtocol
    ) -> SessionCookieBackend:
        return SessionCookieBackend(
            session_repository=(await resolver.resolve(InMemorySessionRepository)),
            user_fetcher=cast(
                "Callable[[str], Awaitable[AuthenticatedUserProtocol | None]]",
                (await resolver.resolve(UserService)).get_user,
            ),
            secure=False,  # local demo runs plain http
        )

    async def _build_password_changes(
        self, resolver: ContainerResolverProtocol
    ) -> PasswordChangeService:
        authentication = await resolver.resolve(AuthenticationService)
        return PasswordChangeService(
            password_hasher=await resolver.resolve(PasswordHasherProtocol),
            policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_api(
        self, resolver: ContainerResolverProtocol
    ) -> AuthApiController:
        return AuthApiController(
            authentication=await resolver.resolve(AuthenticationService),
            cookies=await resolver.resolve(SessionCookieBackend),
            sessions=await resolver.resolve(InMemorySessionRepository),
            authz=await resolver.resolve(AuthorizationService),
            password_changes=await resolver.resolve(PasswordChangeService),
        )

    async def _build_seed_service(
        self, resolver: ContainerResolverProtocol
    ) -> DemoSeedService:
        return DemoSeedService(
            user_service=await resolver.resolve(UserService),
            authz=await resolver.resolve(AuthorizationService),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Seed demo data; everything else wires lazily."""
        seeder = await container.resolve(DemoSeedService)
        await seeder.run()
