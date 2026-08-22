"""One-shot demo data seeding for the auth web demo."""

from __future__ import annotations

from typing import Any, cast

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.contracts.auth.roles import RoleDefinition
from lexigram.logging import get_logger

logger = get_logger(__name__)

DEMO_EMAIL = "admin@auth.demo"
DEMO_PASSWORD = "Demo-Password-1"

# Single source of truth for RBAC seeding. AuthConfig.roles is inert today
# (the authorization sub-provider never reads it), so these are pushed into
# AuthorizationService.set_roles() here.
# TODO(framework): consume AuthConfig.users/roles so demos stop hand-seeding.
ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "viewer": {"name": "viewer", "permissions": ["profile:read"]},
    "editor": {
        "name": "editor",
        "permissions": ["articles:*"],
        "inherits": ["viewer"],
    },
    "admin": {"name": "admin", "permissions": ["*"], "inherits": ["editor"]},
}


class DemoSeedService:
    """Seed the demo account and RBAC roles exactly once."""

    def __init__(self, user_service: UserService, authz: AuthorizationService) -> None:
        self._user_service = user_service
        self._authz = authz

    async def run(self) -> None:
        """Create the demo admin if absent and install role definitions."""
        seeded = await self._user_service.create_user(
            name="Demo Admin",
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            roles=["admin"],
        )
        if seeded.is_err():
            logger.info("seed_user_present", email=DEMO_EMAIL)
        self._authz.set_roles(
            cast("dict[str, RoleDefinition | dict[str, Any]]", ROLE_DEFINITIONS)
        )


__all__ = ["DEMO_EMAIL", "DEMO_PASSWORD", "ROLE_DEFINITIONS", "DemoSeedService"]
