"""DI wiring for the MFA console demo.

Canonical shape: ``register()`` declares bindings; ``boot()`` resolves the
auth stack, rebinds concrete instances via ``container.bind()``, seeds the
demo personas and pre-enrolls the TOTP operator.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, cast

from mfa_console.controllers.api import MfaApiController
from mfa_console.repository.session_repository import InMemorySessionRepository
from mfa_console.ui.pages import PagesController

from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.mfa.manager import MFAManager
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth import AuthenticatedUserProtocol
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

PLAIN_EMAIL = "plain@mfa.demo"
MFA_EMAIL = "mfa@mfa.demo"
DEMO_PASSWORD = "Demo-Password-1"

__all__ = ["DEMO_PASSWORD", "MFA_EMAIL", "PLAIN_EMAIL", "MfaProvider"]


class MfaProvider(Provider):
    """Seed users, enroll the MFA persona, and wire the console."""

    name = "mfa-console"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the MFA stack."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; cross-service wiring happens in :meth:`boot`."""
        repository = InMemorySessionRepository()
        container.singleton(InMemorySessionRepository, instance=repository)
        container.singleton(SessionRepositoryProtocol, instance=repository)
        container.singleton(UserService, UserService)
        container.singleton(MFAManager, MFAManager)
        container.singleton(SessionCookieBackend, SessionCookieBackend)
        container.singleton(MfaApiController, MfaApiController)
        container.singleton(PagesController, PagesController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve the auth stack, seed personas, enroll TOTP, bind wiring."""
        authentication = await container.resolve(AuthenticationService)

        user_service = UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )
        container.bind(UserService, user_service)

        mfa = MFAManager(user_store=user_service.user_store)
        container.bind(MFAManager, mfa)

        container.bind(
            SessionCookieBackend,
            SessionCookieBackend(
                session_repository=await container.resolve(InMemorySessionRepository),
                user_fetcher=cast(
                    "Callable[[str], Awaitable[AuthenticatedUserProtocol | None]]",
                    user_service.get_user,
                ),
                secure=False,  # local demo runs plain http
            ),
        )

        await self._seed_personas(user_service)
        await self._enroll_mfa_persona(user_service, mfa)

        container.bind(
            MfaApiController,
            MfaApiController(
                authentication=authentication,
                users=user_service,
                mfa=mfa,
                cookies=await container.resolve(SessionCookieBackend),
                sessions=await container.resolve(InMemorySessionRepository),
            ),
        )

    async def _seed_personas(self, users: UserService) -> None:
        """Create the two demo personas if absent."""
        for name, email in (
            ("Plain User", PLAIN_EMAIL),
            ("Careful User", MFA_EMAIL),
        ):
            created = await users.create_user(
                name=name, email=email, password=DEMO_PASSWORD
            )
            if created.is_err():
                logger.info("seed_user_present", email=email)

    async def _enroll_mfa_persona(self, users: UserService, mfa: MFAManager) -> None:
        """Pre-enroll the mfa@ persona; tests compute RFC 6238 codes over it."""
        mfa_user = await users.user_store.get_user_by_email(MFA_EMAIL)
        if mfa_user is None:
            return
        profile_mfa = (mfa_user.profile or {}).get("mfa") or {}
        if not profile_mfa.get("enabled"):
            await mfa.enable_totp(mfa_user.user_id, issuer="auth-mfa-demo")
