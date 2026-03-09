"""Authentication (AuthN) - Identity verification and session management"""

from __future__ import annotations

from lexigram.auth.authn._binding import TokenBindingConfig
from lexigram.auth.authn.account_verification import AccountVerificationService
from lexigram.auth.authn.api_key import APIKeyAuthenticator, APIKeyConfig
from lexigram.auth.authn.blacklist import JWTBlacklist
from lexigram.auth.authn.google_oauth import GoogleOAuthService
from lexigram.auth.authn.jwt import JWTTokenManager
from lexigram.auth.authn.oauth2 import OAuth2IdentityProvider, OAuth2Manager
from lexigram.auth.authn.password_reset import PasswordResetService
from lexigram.auth.authn.relay import RelayApiKeyVerifier
from lexigram.auth.authn.schemas import (
    LoginRequest,
    OAuth2AuthorizeRequest,
    OAuth2TokenRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from lexigram.auth.authn.security import PasswordHasher, PasswordPolicy
from lexigram.auth.authn.services import (
    AuthenticationService,
    LockoutConfig,
    LoginAttemptTracker,
)
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.models.user import User
from lexigram.contracts.auth.user import AuthenticatedUserProtocol

__all__ = [
    "APIKeyAuthenticator",
    "APIKeyConfig",
    "AccountVerificationService",
    "AuthenticatedUserProtocol",
    "AuthenticationService",
    "GoogleOAuthService",
    "JWTBlacklist",
    "JWTTokenManager",
    "LockoutConfig",
    "LoginAttemptTracker",
    "LoginRequest",
    "OAuth2AuthorizeRequest",
    "OAuth2IdentityProvider",
    "OAuth2Manager",
    "OAuth2TokenRequest",
    "PasswordHasher",
    "PasswordPolicy",
    "PasswordResetConfirm",
    "PasswordResetRequest",
    "PasswordResetService",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RelayApiKeyVerifier",
    "TokenBindingConfig",
    "TokenResponse",
    "User",
    "UserProfile",
    "UserService",
]
