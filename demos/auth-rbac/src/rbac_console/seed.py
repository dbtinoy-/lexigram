"""One-shot demo data seeding for the RBAC console."""

from __future__ import annotations

from typing import Any, cast

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.contracts.auth.roles import RoleDefinition
from lexigram.logging import get_logger
from rbac_console.articles import ArticleStore
from rbac_console.personas import PERSONAS, PersonaDirectory

logger = get_logger(__name__)

PERSONA_PASSWORD = "Demo-Password-1"

# Single source of truth for role seeding. AuthConfig.roles is inert today,
# so these go into AuthorizationService.set_roles() here. The grammar is
# `resource.action` with bidirectional `*` wildcards.
# TODO(framework): consume AuthConfig.roles so demos stop hand-seeding.
ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "viewer": {"name": "viewer", "permissions": ["articles.view"]},
    "editor": {
        "name": "editor",
        "permissions": ["articles.*"],
        "inherits": ["viewer"],
    },
    "admin": {"name": "admin", "permissions": ["*"], "inherits": ["editor"]},
}


class RbacSeedService:
    """Seed personas, roles, and starter articles exactly once."""

    def __init__(
        self,
        users: UserService,
        authz: AuthorizationService,
        personas: PersonaDirectory,
        articles: ArticleStore,
    ) -> None:
        self._users = users
        self._authz = authz
        self._personas = personas
        self._articles = articles

    async def run(self) -> None:
        """Create persona accounts, install roles, and add starter articles."""
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

        self._authz.set_roles(
            cast("dict[str, RoleDefinition | dict[str, Any]]", ROLE_DEFINITIONS)
        )

        self._articles.create("Welcome", "Articles are guarded by RBAC patterns.")
        self._articles.create("Second", "Try creating one as different personas.")


__all__ = ["PERSONA_PASSWORD", "ROLE_DEFINITIONS", "RbacSeedService"]
