"""DI wiring for the RBAC console demo.

A Provider tells the DI container *what* exists and *how* to build it.
Two-phase lifecycle: ``register()`` binds, ``boot()`` initializes.

Simplest patterns for new users:

- ``container.singleton(Thing, instance=Thing())`` — already built, hand it over
- ``container.singleton(Thing, factory=lambda: ...)`` — build lazily on first resolve
- ``container.singleton(Thing, factory=self._build_thing)`` — async factory for complex wiring

Don't re-register framework keys (e.g. ``AuthorizationService``) — the
auth bundle already owns them.
"""

from __future__ import annotations

from rbac_console.controllers.api import RbacApiController
from rbac_console.data.seed import RbacSeedService
from rbac_console.domain.articles import ArticleStore
from rbac_console.domain.personas import PersonaDirectory
from rbac_console.repository.session_repository import InMemorySessionRepository

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["RbacProvider"]


class RbacProvider(Provider):
    """Wire the demo services; seeding runs once at boot."""

    name = "rbac-console"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind demo services — no I/O here."""

        # --- Stores: trivial objects, bind as instances ---
        repository = InMemorySessionRepository()
        container.singleton(InMemorySessionRepository, instance=repository)
        container.singleton(SessionRepositoryProtocol, instance=repository)
        container.singleton(ArticleStore, instance=ArticleStore())
        container.singleton(PersonaDirectory, instance=PersonaDirectory())

        # --- Services that need auth dependencies: async factories ---
        async def build_users(resolver):
            from lexigram.auth.authn.services import AuthenticationService

            authn = await resolver.resolve(AuthenticationService)
            return UserService(
                password_policy=authn.password_policy,
                user_store=authn.user_store,
            )

        async def build_cookies(resolver):
            return SessionCookieBackend(
                session_repository=await resolver.resolve(InMemorySessionRepository),
                user_fetcher=(await resolver.resolve(UserService)).get_user,
                secure=False,
            )

        container.singleton(UserService, factory=build_users)
        container.singleton(SessionCookieBackend, factory=build_cookies)

        # --- Demo-specific: controller and seeder ---
        async def build_api(resolver):
            return RbacApiController(
                users=await resolver.resolve(UserService),
                authz=await resolver.resolve(AuthorizationService),
                cookies=await resolver.resolve(SessionCookieBackend),
                personas=await resolver.resolve(PersonaDirectory),
                articles=await resolver.resolve(ArticleStore),
            )

        async def build_seed(resolver):
            return RbacSeedService(
                users=await resolver.resolve(UserService),
                authz=await resolver.resolve(AuthorizationService),
                personas=await resolver.resolve(PersonaDirectory),
                articles=await resolver.resolve(ArticleStore),
            )

        container.singleton(RbacApiController, factory=build_api)
        container.singleton(RbacSeedService, factory=build_seed)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Seed personas and articles — I/O is allowed here."""
        seeder = await container.resolve(RbacSeedService)
        await seeder.run()
