"""Authentication provider - handles user authentication only."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import SecretStr

from lexigram.auth.authn.security import PasswordHasher, PasswordPolicy
from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.storage.token_store import InMemoryUserStore, UserStoreProtocol
from lexigram.contracts import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.auth import PasswordHasherProtocol, PasswordPolicyProtocol
from lexigram.contracts.core import HookRegistryProtocol
from lexigram.di.decorators import inject
from lexigram.di.markers import Inject
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

__all__ = ["AuthenticationProvider"]


from lexigram.result import Err, Result

if TYPE_CHECKING:
    from lexigram.auth.config import AuthConfig
    from lexigram.auth.mfa.manager import MFAManager
    from lexigram.contracts.auth.exceptions import TokenError
    from lexigram.contracts.auth.token import VerifiedToken
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)


def _build_token_manager(
    secret_key: str | None,
    jwt_algorithm: str,
    cache_service: Any,
    required_audience: str | None = None,
) -> Any:
    """Build a JWTTokenManager from the supplied credentials.

    Generates an ephemeral RSA keypair when ``jwt_algorithm`` is RS-family
    and no PEM key is provided via ``secret_key``.

    Args:
        secret_key: HMAC secret or PEM-encoded RSA private key.
        jwt_algorithm: JWT signing algorithm (e.g. "HS256", "RS256").
        cache_service: Optional cache backend for token blacklisting.
        required_audience: Forwarded to :class:`JWTTokenManager`; when set,
            every verified token must carry a matching ``aud`` claim.

    Returns:
        A configured :class:`~lexigram.auth.authn.jwt.JWTTokenManager`.
    """
    from lexigram.auth.authn.jwt import JWTTokenManager

    if jwt_algorithm.startswith(("RS", "PS")):
        if secret_key and "-----BEGIN" in secret_key:
            keys: dict[str, Any] = {"default": {"private": secret_key}}
        else:
            try:
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.primitives.asymmetric import rsa
            except (ImportError, ModuleNotFoundError) as exc:
                raise RuntimeError(
                    "cryptography is required for RS/PS algorithms"
                ) from exc

            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")
            public_pem = (
                private_key.public_key()
                .public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                .decode("utf-8")
            )
            keys = {
                "default": {
                    "private": SecretStr(private_pem),
                    "public": SecretStr(public_pem),
                }
            }
            logger.warning(
                "AuthenticationProvider: generated ephemeral RSA keypair; "
                "provide persistent keys in production",
            )
        return JWTTokenManager(
            current_key_id="default",
            keys=keys,
            algorithm=jwt_algorithm,
            cache_service=cache_service,
            required_audience=required_audience,
        )

    # Symmetric algorithm: use secret_key directly (single-secret mode)
    effective_secret = secret_key or "default-dev-secret-change-in-production"
    return JWTTokenManager(
        current_key_id="default",
        keys={"default": SecretStr(effective_secret)},
        algorithm=jwt_algorithm,
        cache_service=cache_service,
        required_audience=required_audience,
    )


@inject
class AuthenticationProvider(Provider):
    """User authentication ONLY (login/logout/validation).

    ``config`` is the primary parameter and drives all defaults.  The optional
    keyword arguments are *override points* for callers that need to supply
    custom implementations (e.g., a production-grade :class:`UserStoreProtocol` backed
    by a database, or a pre-built token manager).

    Args:
        config: The resolved :class:`~lexigram.auth.config.AuthConfig`.
            JWT credentials (``config.token.secret_key``, ``config.token.algorithm``)
            are used to build a :class:`~lexigram.auth.authn.jwt.JWTTokenManager`
            automatically when no ``token_manager`` override is provided.
        password_policy: Override the password policy derived from ``config.password``.
            When *None* the policy is built from config; falls back to ``PasswordPolicy()``
            when config is also absent.
        user_store: Override the user store.  Defaults to :class:`InMemoryUserStore`.
        token_manager: Supply a fully constructed token manager.  When *None* and
            ``config.token`` is present the manager is built automatically from the
            JWT configuration.
        cache_service: Optional cache backend passed to the auto-built token manager
            for token blacklisting.  Ignored when ``token_manager`` is provided directly.
        mfa_service: Optional MFA manager for multi-factor authentication flows.
    """

    def __init__(
        self,
        config: Annotated[AuthConfig, Inject] | None = None,
        *,
        password_policy: PasswordPolicy | None = None,
        user_store: UserStoreProtocol | None = None,
        token_manager: Any = None,
        cache_service: Any = None,
        mfa_service: MFAManager | None = None,
    ) -> None:
        super().__init__(name="authentication", priority=ProviderPriority.SECURITY)
        self.config = config
        if password_policy is not None:
            self.password_policy = password_policy
        elif config is not None and config.password is not None:
            self.password_policy = PasswordPolicy.from_config(config.password)
        else:
            self.password_policy = PasswordPolicy()
        self.user_store = user_store or InMemoryUserStore()
        self.mfa_service = mfa_service

        # Auto-create a JWTTokenManager from config when no override is supplied.
        if (
            token_manager is None
            and config is not None
            and getattr(config, "token", None) is not None
        ):
            token_manager = _build_token_manager(
                secret_key=config.token.secret_key,
                jwt_algorithm=config.token.algorithm,
                cache_service=cache_service,
                required_audience=config.token.required_audience,
            )

        self.token_manager = token_manager
        self.delegation_manager: Any = None
        self._service: AuthenticationService | None = None

    @property
    def service(self) -> AuthenticationService:
        """Get or create the authentication service."""
        if self._service is None:
            self._service = AuthenticationService(
                password_policy=self.password_policy,
                user_store=self.user_store,
                token_manager=self.token_manager,
            )
        return self._service

    async def get_user(self, user_id: str) -> Any | None:
        """Fetch a user by their ID.

        Satisfies :class:`~lexigram.contracts.auth.AuthProviderProtocol`.

        Args:
            user_id: The unique identifier of the user to retrieve.

        Returns:
            The user object, or ``None`` if not found.
        """
        return await self.user_store.get_user_by_id(user_id)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register authentication services with the container.

        Registers both concrete implementations and their corresponding protocols
        to enable dependency injection across extensions without direct imports.
        """
        hasher = PasswordHasher()
        # Register concrete implementations
        container.singleton(PasswordHasher, hasher)
        container.singleton(PasswordPolicy, lambda: self.password_policy)
        container.singleton(UserStoreProtocol, lambda: self.user_store)
        container.singleton(AuthenticationService, lambda: self.service)

        # Register protocol mappings for cross-extension compatibility (CROSS-EXT-02)
        # This allows other extensions to depend on protocols rather than concrete classes
        container.singleton(PasswordHasherProtocol, hasher)
        container.singleton(PasswordPolicyProtocol, lambda: self.password_policy)
        from lexigram.contracts.auth import AuthProviderProtocol

        # Only register self as AuthProviderProtocol when no other provider
        # has already claimed this slot (e.g., an application-level AuthService).
        if not container.has(AuthProviderProtocol):
            container.singleton(AuthProviderProtocol, lambda: self)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Initialize authentication provider and register with kernel health registry."""
        logger.info("AuthenticationProvider started")
        hooks = await container.resolve_optional(HookRegistryProtocol)
        self.service.set_hook_registry(hooks)
        if self.token_manager is not None and hasattr(
            self.token_manager, "set_hook_registry"
        ):
            self.token_manager.set_hook_registry(hooks)
        if container is not None and hasattr(container, "resolve"):
            with contextlib.suppress(
                ImportError, AttributeError, RuntimeError, TypeError
            ):
                from lexigram.contracts.observability.metrics import (
                    HealthCheckRegistryProtocol,
                )

                registry = await container.resolve(HealthCheckRegistryProtocol)
                registry.add("authentication", self.health_check)

    async def shutdown(self) -> None:
        """Shutdown authentication provider."""
        logger.info("AuthenticationProvider shutdown")

    async def verify_token(self, token: str) -> Result[VerifiedToken, TokenError]:
        """Verify a JWT token and return a ``Result`` with the decoded payload.

        Satisfies :class:`~lexigram.contracts.auth.AuthProviderProtocol`.

        Delegates to ``token_manager.verify_token()`` when a token manager
        is configured.  Returns an ``Err`` result if no token manager is set
        or if the token is invalid for any expected domain reason.

        Infrastructure failures (cache unavailable, network errors) are still
        raised as exceptions and must be handled by the caller.

        Args:
            token: The JWT token string to verify.

        Returns:
            ``Ok(VerifiedToken)`` if the token is valid and not revoked,
            or ``Err(TokenError)`` for expected domain failures.
        """
        from lexigram.auth.exceptions import TokenInvalidError

        if self.token_manager is None:
            return Err(TokenInvalidError("Authentication not configured"))  # type: ignore[arg-type]
        return await self.token_manager.verify_token(token)

    async def validate_session(self, token: str) -> Any:
        """Validate a session token and return user information.

        Delegates to the underlying authentication service's
        ``get_user_from_token`` method.  Returns a
        ``Result[VerifiedToken, TokenError]`` or ``None`` when no token
        manager is configured.

        Args:
            token: The session or JWT token to validate.

        Returns:
            ``Result[VerifiedToken, TokenError]`` on success/failure, or ``None``.
        """
        if self.token_manager is None:
            return None
        return await self.service.get_user_from_token(token)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check authentication provider health."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={
                "service": "authentication",
                "password_policy": str(self.password_policy),
                "user_store_type": type(self.user_store).__name__,
            },
        )
