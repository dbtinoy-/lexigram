"""DI wiring for the RBAC console demo."""

from __future__ import annotations

from typing import Any

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth import UserStoreProtocol
from lexigram.contracts.auth.protocols import PasswordPolicyProtocol
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

from rbac_console.articles import ArticleStore
from rbac_console.personas import PersonaDirectory
from rbac_console.controllers.api import PERSONAS, RbacApiController
from rbac_console.session_repository import InMemorySessionRepository
from rbac_console.ui.pages import PagesController

logger = get_logger(__name__)

PERSONA_PASSWORD = "Demo-Password-1"

# Single source of truth for role seeding. AuthConfig.roles is inert today,
# so these go into AuthorizationService.set_roles() at boot. The grammar is
# `resource.action` with bidirectional `*` wildcards.
ROLE_DEFINITIONS: dict[str, dict[str, object]] = {
    "viewer": {"name": "viewer", "permissions": ["articles.view"]},
    "editor": {
        "name": "editor",
        "permissions": ["articles.*"],
        "inherits": ["viewer"],
    },
    "admin": {"name": "admin", "permissions": ["*"], "inherits": ["editor"]},
}


class RbacProvider(Provider):
    """Seed personas/roles/articles and wire the console services."""

    name = "rbac-console"

    def __init__(self) -> None:
        super().__init__()
        self._repository = InMemorySessionRepository()
        self._articles = ArticleStore()
        self._personas = PersonaDirectory()
        self._users: UserService | None = None
        self._authz: AuthorizationService | None = None
        self._cookies: SessionCookieBackend | None = None
        self._api: RbacApiController | None = None

    def _get(self, kind: str):
        """Return a boot-assembled collaborator (None before boot).

        Freeze-time dependency validation resolves these factories before
        any provider boots, so they must succeed with ``None`` rather than
        raise — real values land when :meth:`boot` runs.
        """
        return getattr(self, kind)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register keys up front; boot() fills the instances (factory pattern)."""
        container.singleton(InMemorySessionRepository, instance=self._repository)
        container.singleton(SessionRepositoryProtocol, instance=self._repository)
        container.singleton(ArticleStore, instance=self._articles)
        container.singleton(UserService, factory=lambda: self._get("_users"))
        # NOTE: do NOT re-register AuthorizationService here — the auth
        # bundle owns that key; resolving it below picks up its singleton.
        container.singleton(SessionCookieBackend, factory=lambda: self._get("_cookies"))
        container.singleton(RbacApiController, factory=lambda: self._get("_api"))
        container.singleton(PagesController, instance=PagesController())
        container.singleton(PersonaDirectory, instance=self._personas)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Seed roles/personas/articles and assemble the controller."""
        from lexigram.auth.authn.services import AuthenticationService

        authentication = await container.resolve(AuthenticationService)

        # UserService on the SAME store/policy AuthenticationService holds
        # (the protocol keys sit behind module export visibility; the
        # concrete service's public attributes are the sanctioned path).
        self._users = UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

        for persona in PERSONAS:
            created = await self._users.create_user(
                name=f"{persona.title()} Persona",
                email=f"{persona}@rbac.demo",
                password=PERSONA_PASSWORD,
                roles=[persona],
            )
            if created.is_err():
                logger.info("persona_present", persona=persona)
            else:
                self._personas.register(persona, created.unwrap())

        self._authz = await container.resolve(AuthorizationService)
        self._authz.set_roles(ROLE_DEFINITIONS)

        self._articles.create("Welcome", "Articles are guarded by RBAC patterns.")
        self._articles.create("Second", "Try creating one as different personas.")

        self._cookies = SessionCookieBackend(
            session_repository=self._repository,
            user_fetcher=self._users.get_user,
            secure=False,  # local demo runs plain http
        )
        self._api = RbacApiController(
            users=self._users,
            authz=self._authz,
            cookies=self._cookies,
            personas=self._personas,
            articles=self._articles,
        )


__all__ = ["PERSONA_PASSWORD", "ROLE_DEFINITIONS", "RbacProvider"]
