"""DI wiring for the auth web demo."""

from __future__ import annotations

from typing import Any

from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.config import AuthConfig, JWTConfig
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.contracts.auth.repositories import SessionRepositoryProtocol
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

from auth_web.controllers.pages import AuthWebController
from auth_web.services.session_repository import InMemorySessionRepository

logger = get_logger(__name__)

DEMO_EMAIL = "admin@auth.demo"
DEMO_PASSWORD = "Demo-Password-1"


def build_auth_config() -> AuthConfig:
    """Offline demo config: explicit dev secrets and RBAC role definitions.

    Note:
        ``AuthConfig.users`` is inert today (nothing consumes it at boot),
        so the demo account is seeded explicitly in :meth:`AuthWebProvider.boot`.
    """
    secret = "auth-web-demo-secret-key-0123456789abcdef"
    return AuthConfig(
        secret_key=secret,
        token=JWTConfig(secret_key=secret),
        roles={
            "viewer": {"name": "viewer", "permissions": ["profile:read"]},
            "editor": {
                "name": "editor",
                "permissions": ["articles:*"],
                "inherits": ["viewer"],
            },
            "admin": {
                "name": "admin",
                "permissions": ["*"],
                "inherits": ["editor"],
            },
        },
    )


class AuthWebProvider(Provider):
    """Assemble the demo's session layer and register UI services."""

    name = "auth-web"

    def __init__(self) -> None:
        super().__init__()
        self._repository = InMemorySessionRepository()
        self._user_service: UserService | None = None
        self._backend: SessionCookieBackend | None = None
        self._controller: AuthWebController | None = None

    def _get(self, kind: str) -> Any:
        """Return a boot-assembled collaborator or raise."""
        value = getattr(self, kind)
        if value is None:
            raise RuntimeError(f"AuthWebProvider has not been booted yet ({kind})")
        return value

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register every key the controller needs; boot fills instances.

        Freeze-time validation requires all constructor dependencies to be
        present as keys, so each is bound here — the pure repository as a
        live instance, the boot-built collaborators as lazy factories.
        """
        container.singleton(InMemorySessionRepository, instance=self._repository)
        container.singleton(SessionRepositoryProtocol, instance=self._repository)
        container.singleton(UserService, factory=lambda: self._get("_user_service"))
        container.singleton(SessionCookieBackend, factory=lambda: self._get("_backend"))
        container.singleton(AuthWebController, factory=lambda: self._get("_controller"))

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve auth singletons; seed the demo user; build UI services."""
        authentication = await container.resolve(AuthenticationService)

        # UserService ships unregistered: build it on the SAME policy/user
        # store AuthenticationService holds so password changes are visible
        # to login. (The protocol keys themselves sit behind module export
        # visibility; the concrete service's public attributes are the
        # sanctioned access path.)
        self._user_service = UserService(
            password_policy=authentication.password_policy,
            user_store=authentication.user_store,
        )

        # Seed the demo account. AuthConfig.users is inert in the framework
        # today, so boot-time seeding here is what makes login work.
        seeded = await self._user_service.create_user(
            name="Demo Admin",
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            roles=["admin"],
        )
        if seeded.is_err():
            logger.info("seed_user_present", email=DEMO_EMAIL)
        probe = await self._user_service.list_users()

        self._backend = SessionCookieBackend(
            session_repository=self._repository,
            user_fetcher=self._user_service.get_user,
            secure=False,  # local demo runs plain http
        )
        self._controller = AuthWebController(
            authentication=authentication,
            users=self._user_service,
            cookies=self._backend,
            sessions=self._repository,
        )


__all__ = [
    "DEMO_EMAIL",
    "DEMO_PASSWORD",
    "AuthWebProvider",
    "build_auth_config",
]
