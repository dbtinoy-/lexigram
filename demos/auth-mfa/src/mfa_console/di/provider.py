"""DI wiring for the MFA console demo."""

from __future__ import annotations

from mfa_console.controllers.api import MfaApiController
from mfa_console.repository.session_repository import InMemorySessionRepository
from mfa_console.ui.pages import PagesController

from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.auth.mfa.manager import MFAManager
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

logger = get_logger(__name__)

PLAIN_EMAIL = "plain@mfa.demo"
MFA_EMAIL = "mfa@mfa.demo"
DEMO_PASSWORD = "Demo-Password-1"


class MfaProvider(Provider):
    """Seed users, enroll the MFA persona, and wire the console."""

    name = "mfa-console"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness."""
        return HealthCheckResult(component=self.name)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind builders; collaborators resolve lazily via the container."""
        repository = InMemorySessionRepository()
        container.singleton(InMemorySessionRepository, instance=repository)
        container.singleton(SessionRepositoryProtocol, instance=repository)
        container.singleton(UserService, factory=self._build_user_service)
        container.singleton(MFAManager, factory=self._build_mfa_manager)
        container.singleton(SessionCookieBackend, factory=self._build_session_backend)
        container.singleton(MfaApiController, factory=self._build_api)
        container.singleton(PagesController, instance=PagesController())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Seed demo accounts and enroll the MFA persona."""
        users = await container.resolve(UserService)
        mfa = await container.resolve(MFAManager)

        for name, email in (
            ("Plain User", PLAIN_EMAIL),
            ("Careful User", MFA_EMAIL),
        ):
            created = await users.create_user(
                name=name, email=email, password=DEMO_PASSWORD
            )
            if created.is_err():
                logger.info("seed_user_present", email=email)

        mfa_user = await users.user_store.get_user_by_email(MFA_EMAIL)
        if mfa_user is not None:
            profile_mfa = (mfa_user.profile or {}).get("mfa") or {}
            if not profile_mfa.get("enabled"):
                await mfa.enable_totp(mfa_user.user_id, issuer="auth-mfa-demo")

    async def _build_user_service(
        self, resolver: ContainerResolverProtocol
    ) -> UserService:
        """Build UserService on the SAME policy/store AuthenticationService
        holds, so seeded users are visible to login."""
        authentication = await resolver.resolve(AuthenticationService)
        return UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

    async def _build_mfa_manager(
        self, resolver: ContainerResolverProtocol
    ) -> MFAManager:
        user_service = await resolver.resolve(UserService)
        return MFAManager(user_store=user_service.user_store)

    async def _build_session_backend(
        self, resolver: ContainerResolverProtocol
    ) -> SessionCookieBackend:
        repository = await resolver.resolve(InMemorySessionRepository)
        user_service = await resolver.resolve(UserService)
        return SessionCookieBackend(
            session_repository=repository,
            user_fetcher=user_service.get_user,
            secure=False,  # local demo runs plain http
        )

    async def _build_api(self, resolver: ContainerResolverProtocol) -> MfaApiController:
        authentication = await resolver.resolve(AuthenticationService)
        user_service = await resolver.resolve(UserService)
        mfa = await resolver.resolve(MFAManager)
        cookies = await resolver.resolve(SessionCookieBackend)
        sessions = await resolver.resolve(InMemorySessionRepository)

        # Seed the demo accounts. AuthConfig.users is inert today.
        for name, email in (
            ("Plain User", PLAIN_EMAIL),
            ("Careful User", MFA_EMAIL),
        ):
            created = await user_service.create_user(
                name=name, email=email, password=DEMO_PASSWORD
            )
        import sys

        print(
            "BUILD-API RAN; store:",
            type(user_service.user_store).__name__,
            file=sys.stderr,
        )
        if created.is_err():
            logger.info("seed_user_present", email=email)
        probe_users = await user_service.list_users()
        logger.warning(
            "seed_probe",
            emails=[u.email for u in probe_users],
            store_type=type(user_service.user_store).__name__,
            authn_store_type=type(authentication.user_store).__name__,
            same_store=user_service.user_store is authentication.user_store,
        )

        # Pre-enroll the mfa@ persona for this process; tests read the secret
        # back from the profile and compute RFC 6238 codes over it.
        mfa_user = await user_service.user_store.get_user_by_email(MFA_EMAIL)
        if mfa_user is not None:
            profile_mfa = (mfa_user.profile or {}).get("mfa") or {}
            if not profile_mfa.get("enabled"):
                await mfa.enable_totp(mfa_user.user_id, issuer="auth-mfa-demo")

        return MfaApiController(
            authentication=authentication,
            users=user_service,
            mfa=mfa,
            cookies=cookies,
            sessions=sessions,
        )


def build_auth_config() -> AuthConfig:
    """Offline demo config with an explicit dev secret."""
    secret = "mfa-console-demo-secret-key-0123456789abc"
    return AuthConfig(
        secret_key=secret,
        token=JWTConfig(secret_key=secret),
    )


__all__ = [
    "DEMO_PASSWORD",
    "MFA_EMAIL",
    "PLAIN_EMAIL",
    "MfaProvider",
    "build_auth_config",
]
