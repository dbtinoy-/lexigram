"""User service — registration, authentication, and profile operations.

:class:`UserService` encapsulates all identity operations.  It depends on
repository and auth primitives via **constructor injection** — no service
locator, no global state.

All domain operations return ``Result[T, E]`` so callers can pattern-match
outcomes without catching exceptions for control flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.exceptions.domain import DomainError, NotFoundError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_api.domain.user import User, UserCreated

if TYPE_CHECKING:
    from lexigram.auth.authn.jwt import JWTTokenManager
    from lexigram.auth.authn.security import PasswordHasher
    from lexigram.auth.models.user import User as AuthUser
    from lexigram.contracts.events.protocols import DomainEventPublisherProtocol

    from lexigram_example_api.repositories.user_repository import UserRepositoryProtocol

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------


class EmailAlreadyRegistered(DomainError):
    """Raised when a registration is attempted with a duplicate email.

    Attributes:
        email: The email address that is already in use.
    """

    def __init__(self, email: str) -> None:
        """Initialise with the duplicate email address.

        Args:
            email: The already-registered email address.
        """
        super().__init__(f"Email already registered: {email}")
        self.email = email


class InvalidCredentials(DomainError):
    """Raised when login credentials do not match any account."""

    def __init__(self) -> None:
        """Initialise with a generic message to avoid email enumeration."""
        super().__init__("Invalid email or password")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class UserService:
    """Domain service for user identity operations.

    Handles registration, authentication, and profile retrieval.  Publishes
    domain events to the event bus on state-changing operations.

    Args:
        repo: Repository for user persistence.
        hasher: Password hashing utility from lexigram-auth.
        jwt_manager: JWT token manager for access-token creation / validation.
        event_publisher: Domain event publisher.
    """

    def __init__(
        self,
        repo: UserRepositoryProtocol,
        hasher: PasswordHasher,
        jwt_manager: JWTTokenManager,
        event_publisher: DomainEventPublisherProtocol,
    ) -> None:
        """Initialise UserService with injected dependencies.

        Args:
            repo: Repository for user persistence.
            hasher: Password hashing utility from lexigram-auth.
            jwt_manager: JWT token manager for access-token creation / validation.
            event_publisher: Domain event publisher.
        """
        self._repo = repo
        self._hasher = hasher
        self._jwt = jwt_manager
        self._events = event_publisher

    async def register(
        self,
        email: str,
        password: str,
    ) -> Result[User, DomainError]:
        """Register a new user account.

        Hashes the password, persists the user, and publishes
        :class:`~lexigram_example_api.domain.user.UserCreated`.

        Args:
            email: The user's email address (uniqueness enforced).
            password: Plain-text password; hashed before storage.

        Returns:
            ``Ok(User)`` on success, or:
            - ``Err(EmailAlreadyRegistered)`` if the email is taken.
        """
        existing = await self._repo.find_by_email(email)
        if existing is not None:
            logger.info("register_email_taken", email=email)
            return Err(EmailAlreadyRegistered(email))

        hashed = await self._hasher.hash(password)
        user = User(email=email.lower(), hashed_password=hashed)
        saved = await self._repo.save(user)

        await self._events.publish(
            UserCreated(user_id=saved.user_id, email=saved.email)
        )
        logger.info("user_registered", user_id=saved.user_id)
        return Ok(saved)

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Result[str, DomainError]:
        """Authenticate a user and return a signed JWT access token.

        Args:
            email: The user's email address.
            password: The plain-text password to verify.

        Returns:
            ``Ok(token)`` where ``token`` is a signed JWT string, or:
            - ``Err(InvalidCredentials)`` if the email is unknown or password wrong.
        """
        user = await self._repo.find_by_email(email)
        if user is None:
            logger.info("auth_email_not_found", email=email)
            return Err(InvalidCredentials())

        if not await self._hasher.verify(password, user.hashed_password):
            logger.info("auth_wrong_password", user_id=user.user_id)
            return Err(InvalidCredentials())

        # Build a lightweight auth-layer User to pass to JWTTokenManager
        # (avoids importing from lexigram.auth in domain/service layers)
        token = self._jwt.create_access_token(self._to_auth_user(user))
        logger.info("user_authenticated", user_id=user.user_id)
        return Ok(token)

    async def find_by_id(self, user_id: str) -> Result[User, DomainError]:
        """Retrieve a user profile by their stable identifier.

        Args:
            user_id: UUID string of the user to look up.

        Returns:
            ``Ok(User)`` if found, or ``Err(NotFoundError)`` otherwise.
        """
        user = await self._repo.find_by_id(user_id)
        if user is None:
            return Err(NotFoundError(f"User not found: {user_id}"))
        return Ok(user)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _to_auth_user(self, user: User) -> AuthUser:
        """Adapt a domain User to a lexigram-auth User for token creation.

        Args:
            user: Domain user entity.

        Returns:
            A ``lexigram.auth.models.user.User`` suitable for JWT creation.
        """
        from lexigram.auth.models.user import User as AuthUserModel

        return AuthUserModel(
            user_id=user.user_id,
            email=user.email,
            is_active=user.is_active,
            roles=[],
            permissions=[],
        )
