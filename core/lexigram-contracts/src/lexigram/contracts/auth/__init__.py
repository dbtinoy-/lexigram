"""Authentication and authorization protocols."""

from __future__ import annotations

from lexigram.contracts.auth.blacklist import TokenBlacklistProtocol
from lexigram.contracts.auth.exceptions import (
    AuthError,
    TokenError,
    VerificationError,
)
from lexigram.contracts.auth.guard import AuthenticatorProtocol, AuthorizerProtocol
from lexigram.contracts.auth.identity import IdentityResolverProtocol
from lexigram.contracts.auth.models import (
    UserIdentityProtocol,
    UserSession,
    VerifiedIdentityClaims,
)
from lexigram.contracts.auth.policy import PolicyStoreProtocol
from lexigram.contracts.auth.protocols import (
    AuthProviderProtocol,
    LoginAttemptTrackerProtocol,
    MFAManagerProtocol,
    PasswordHasherProtocol,
    PasswordPolicyProtocol,
)
from lexigram.contracts.auth.repositories import (
    APIKeyRepositoryProtocol,
    SessionRepositoryProtocol,
)
from lexigram.contracts.auth.roles import RoleDefinition
from lexigram.contracts.auth.store import (
    UserReaderProtocol,
    UserStoreProtocol,
    UserWriterProtocol,
)
from lexigram.contracts.auth.token import TokenManagerProtocol, VerifiedToken
from lexigram.contracts.auth.user import AuthenticatedUserProtocol, UserProtocol

__all__ = [
    "APIKeyRepositoryProtocol",
    "AuthError",
    "AuthProviderProtocol",
    "AuthenticatedUserProtocol",
    "AuthenticatorProtocol",
    "AuthorizerProtocol",
    "IdentityResolverProtocol",
    "LoginAttemptTrackerProtocol",
    "MFAManagerProtocol",
    "PasswordHasherProtocol",
    "PasswordPolicyProtocol",
    "PolicyStoreProtocol",
    "RoleDefinition",
    "SessionRepositoryProtocol",
    "TokenBlacklistProtocol",
    "TokenError",
    "TokenManagerProtocol",
    "UserIdentityProtocol",
    "UserProtocol",
    "UserReaderProtocol",
    "UserSession",
    "UserStoreProtocol",
    "UserWriterProtocol",
    "VerificationError",
    "VerifiedIdentityClaims",
    "VerifiedToken",
]
