"""DI wiring for the RBAC console demo."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from rbac_console.articles import ArticleStore
from rbac_console.controllers.api import RbacApiController
from rbac_console.personas import PersonaDirectory
from rbac_console.repository.session_repository import InMemorySessionRepository
from rbac_console.seed import (
    PERSONA_PASSWORD,
    ROLE_DEFINITIONS,
    RbacSeedService,
)

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth import AuthenticatedUserProtocol
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

__all__ = ["PERSONA_PASSWORD", "ROLE_DEFINITIONS", "RbacProvider"]


class RbacProvider(Provider):
    """Wire the console services; seeding runs once at boot.

    All boot-built collaborators are resolver-receiving async factories:
    the container invokes them lazily (and awaits them), so the provider
    holds no state and needs no None-guards.
    """

    name = "rbac-console"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the RBAC stack."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind pure instances now; collaborators build lazily post-boot."""
        repository = InMemorySessionRepository()
        container.singleton(InMemorySessionRepository, instance=repository)
        container.singleton(SessionRepositoryProtocol, instance=repository)
        container.singleton(ArticleStore, instance=ArticleStore())
        container.singleton(PersonaDirectory, instance=PersonaDirectory())
        container.singleton(UserService, factory=self._build_users)
        # NOTE: do NOT re-register AuthorizationService here — the auth
        # bundle owns that key; resolving it picks up its singleton.
        container.singleton(SessionCookieBackend, factory=self._build_cookies)
        container.singleton(RbacApiController, factory=self._build_api)
        container.singleton(RbacSeedService, factory=self._build_seed_service)

    async def _build_users(self, resolver: ContainerResolverProtocol) -> UserService:
        from lexigram.auth.authn.services import AuthenticationService

        authentication = await resolver.resolve(AuthenticationService)
        # UserService on the SAME store/policy AuthenticationService holds
        # (the protocol keys sit behind module export visibility; the
        # concrete service's public attributes are the sanctioned path).
        # TODO(framework): export UserService (or its dep keys) so this
        # attribute-fishing disappears.
        return UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_cookies(
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

    async def _build_api(
        self, resolver: ContainerResolverProtocol
    ) -> RbacApiController:
        return RbacApiController(
            users=await resolver.resolve(UserService),
            authz=await resolver.resolve(AuthorizationService),
            cookies=await resolver.resolve(SessionCookieBackend),
            personas=await resolver.resolve(PersonaDirectory),
            articles=await resolver.resolve(ArticleStore),
        )

    async def _build_seed_service(
        self, resolver: ContainerResolverProtocol
    ) -> RbacSeedService:
        return RbacSeedService(
            users=await resolver.resolve(UserService),
            authz=await resolver.resolve(AuthorizationService),
            personas=await resolver.resolve(PersonaDirectory),
            articles=await resolver.resolve(ArticleStore),
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Seed roles/personas/articles; everything else wires lazily."""
        seeder = await container.resolve(RbacSeedService)
        await seeder.run()
