"""Boot-time demo seeding — personas, roles, and starter articles.

Teaching focus: **the provider ``boot()`` hook**.  ``register()`` (which
runs first) only *binds* services into the container; ``boot()`` runs
afterwards, when the container is frozen and everything is resolvable.
Seeding belongs in ``boot()`` precisely because it must resolve the real,
fully-wired services — see ``di/provider.py``, which resolves this class
inside ``boot()``.

This module lives in ``data/`` because it's initialization code, not a
runtime service.  It runs once at startup and has no runtime role.

Roles are now defined in ``application.yaml`` under ``auth.roles`` and
auto-consumed by ``AuthorizationProvider`` — no hand-seeding needed.

Also demonstrated: framework services return ``Result`` values
(``UserService.create_user`` → ``Ok``/``Err``), so seeding handles the
"already exists" case by matching on the error instead of pre-checking.
"""

from __future__ import annotations

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.logging import get_logger
from rbac_console.domain.articles import ArticleStore
from rbac_console.domain.personas import PERSONAS, PersonaDirectory

logger = get_logger(__name__)

PERSONA_PASSWORD = "Demo-Password-1"


class RbacSeedService:
    """Seed personas, roles, and starter articles exactly once.

    Constructed by ``RbacProvider._build_seed_service`` during boot; all
    collaborators arrive via constructor injection from the container.

    Named ``data/seed.py`` because it's data initialization, not a runtime
    service.  It runs once at startup and has no ongoing role.
    """

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
            # create_user returns Result[User, ...]: Ok on first run,
            # Err(duplicate) on every later boot — both are fine here.
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

        # Roles are now auto-consumed from AuthConfig.roles by
        # AuthorizationProvider — no hand-seeding needed here.

        self._articles.create("Welcome", "Articles are guarded by RBAC patterns.")
        self._articles.create("Second", "Try creating one as different personas.")


__all__ = ["PERSONA_PASSWORD", "RbacSeedService"]
