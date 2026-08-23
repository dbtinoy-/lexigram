"""One-shot demo data seeding for the API-keys console."""

from __future__ import annotations

from lexigram.auth.authn.user_service import UserService
from lexigram.logging import get_logger

logger = get_logger(__name__)

DEMO_EMAIL = "admin@keys.demo"
DEMO_PASSWORD = "Demo-Password-1"


class DemoSeedService:
    """Seed the demo admin account exactly once.

    TODO(framework): consume ``AuthConfig.users`` so demos stop
    hand-seeding accounts at boot.
    """

    def __init__(self, users: UserService) -> None:
        self._users = users

    async def run(self) -> None:
        """Create the demo admin if absent."""
        created = await self._users.create_user(
            name="Demo Admin",
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            roles=["admin"],
        )
        if created.is_err():
            logger.info("seed_user_present", email=DEMO_EMAIL)


__all__ = ["DEMO_EMAIL", "DEMO_PASSWORD", "DemoSeedService"]
