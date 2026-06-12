"""Type definitions for auth testing utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.auth.authn.core import User
    from lexigram.auth.models import AuthToken

from lexigram.auth.authn.core import User
from lexigram.auth.authn.security import PasswordHasher
from lexigram.auth.models import AuthToken


@dataclass
class AuthTestUser:
    """Test user data for authentication testing.

    Attributes:
        user_id: Unique user identifier
        username: Username
        email: Email address
        password: Plain text password (for testing)
        hashed_password: Hashed password
        roles: List of user roles
        permissions: List of user permissions
        is_active: Whether user is active
        is_verified: Whether user is verified
        profile: Additional profile data
    """

    user_id: str
    username: str
    email: str
    password: str
    hashed_password: str | None
    roles: list[str] = field(default_factory=lambda: ["user"])
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True
    is_verified: bool = True
    profile: dict[str, Any] = field(default_factory=dict)

    @classmethod
    async def create(
        cls,
        username: str,
        email: str,
        password: str = "password123",  # noqa: S107  # intentional default for test users
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        **kwargs: Any,
    ) -> AuthTestUser:
        """Create a test user with default values."""
        hashed_password = await PasswordHasher().hash(password)
        return cls(
            user_id=f"user_{username}",
            username=username,
            email=email,
            password=password,
            hashed_password=hashed_password,
            roles=roles or ["user"],
            permissions=permissions or [],
            **kwargs,
        )

    def to_user(self) -> User:
        """Convert to a User instance."""
        return User(
            user_id=self.user_id,
            username=self.username,
            email=self.email,
            hashed_password=self.hashed_password,
            roles=list(self.roles),
            permissions=list(self.permissions),
            is_active=self.is_active,
            is_verified=self.is_verified,
            profile=self.profile,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_login_at=None,
        )


@dataclass
class AuthTestToken:
    """Test token data for authentication testing.

    Attributes:
        access_token: JWT access token
        refresh_token: JWT refresh token
        token_type: Token type (Bearer)
        expires_at: Token expiration datetime
        refresh_expires_at: Refresh token expiration datetime
        user: Associated test user
    """

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    refresh_expires_at: datetime | None = None
    user: AuthTestUser | None = None

    @classmethod
    def create(
        cls,
        user: AuthTestUser,
        expires_at: datetime | None = None,
        refresh_expires_at: datetime | None = None,
    ) -> AuthTestToken:
        """Create a test token for a user."""
        # Generate mock JWT tokens
        access_token = f"mock_access_token_{user.user_id}_{datetime.now().timestamp()}"
        refresh_token = (
            f"mock_refresh_token_{user.user_id}_{datetime.now().timestamp()}"
        )

        if expires_at is None:
            expires_at = datetime.now(UTC) + timedelta(hours=1)
        if refresh_expires_at is None:
            refresh_expires_at = datetime.now(UTC) + timedelta(days=30)

        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            user=user,
        )

    def to_auth_token(self) -> AuthToken:
        """Convert to an AuthToken instance."""
        return AuthToken(
            token=self.access_token,
            expires_at=self.expires_at or datetime.now(UTC),
            refresh_token=self.refresh_token,
            refresh_expires_at=self.refresh_expires_at or datetime.now(UTC),
            token_type=self.token_type,
        )
