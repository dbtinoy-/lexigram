"""
lexigram-auth — Authentication and authorisation for the Lexigram platform.

Canonical import paths
-----------------------
User authentication:   from lexigram.auth.authn.services import AuthenticationService
Token refresh:         from lexigram.auth.authn.services import AuthenticationService
                       await service.refresh_token(existing_refresh_token)
JWT tokens:            from lexigram.auth.authn.jwt import JWTTokenManager
RBAC / authorisation:  from lexigram.auth.authz.service import AuthorizationService
Session management:    from lexigram.auth.session import SessionManagerImpl
OAuth:                 from lexigram.auth.authn.oauth import OAuthService
Account verification:  from lexigram.auth.authn.verification import AccountVerificationService

All commonly-used symbols are also re-exported from this root package so
``from lexigram.auth import JWTTokenManager`` always works.

Key APIs
--------
- ``AuthenticationService.refresh_token(refresh_token: str) -> Result[AuthToken, TokenError]``
  Refresh an expired access token using a refresh token. Returns new access + refresh tokens.
- ``AuthenticationService.authenticate(user_id, password) -> Result[AuthToken, AuthenticationFailed]``
  Authenticate a user with credentials.
- ``AuthorizationService.authorize(user, required_roles) -> Result[True, AuthorizationFailed]``
  Enforce RBAC policies.

GuardProtocol decorators
----------------
``use_guards`` is intentionally **not** exported from this root package.
Use ``lexigram.security.guards.use_guards`` (the canonical, general-purpose
version backed by ``GuardChain``) or the auth-specific decorators
``require_auth``, ``require_roles``, and ``require_permissions``.
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.auth.constants import __version__ as __version__

# =============================================================================
# Lazy Loading to Avoid Circular Imports
# =============================================================================


if TYPE_CHECKING:
    from lexigram.auth.authn.api_key import (
        APIKeyAuthenticator,
        APIKeyConfig,
    )
    from lexigram.auth.authn.google_oauth import GoogleOAuthService
    from lexigram.auth.authn.jwt import JWTTokenManager
    from lexigram.auth.authn.revocation import PersistentTokenRevocationStore
    from lexigram.auth.authn.security import (
        PasswordHasher,
        PasswordPolicy,
    )
    from lexigram.auth.authn.services import (
        AuthenticationService,
        LockoutConfig,
        LoginAttemptTracker,
    )
    from lexigram.auth.authn.user_service import UserService
    from lexigram.auth.authz.guards import (
        optional_auth,
        require_auth,
        require_permissions,
        require_roles,
    )
    from lexigram.auth.config import (
        AuthConfig,
        JWTConfig,
        MFAConfig,
        RBACConfig,
    )
    from lexigram.auth.di import (
        AuthenticationProvider,
        AuthorizationProvider,
        GoogleOAuthProvider,
    )
    from lexigram.auth.di.bundle_provider import AuthBundleProvider
    from lexigram.auth.events import (
        AuthenticationFailed,
        PasswordChanged,
        SessionCreated,
        SessionRevoked,
        TokenRevoked,
        UserAuthenticated,
        UserLockedOut,
        UserLoggedIn,
        UserLoggedOut,
        UserLoginFailed,
        UserRegistered,
    )
    from lexigram.auth.exceptions import (
        AlreadyVerifiedError,
        AuthenticationError,
        AuthError,
        AuthorizationError,
        InvalidTokenError,
        TokenAudienceError,
        TokenBlacklistedError,
        TokenError,
        TokenExpiredError,
        TokenExpiredVerificationError,
        TokenInvalidError,
        TokenNotFoundError,
        VerificationError,
    )
    from lexigram.auth.models import (
        AuthToken,
        User,
    )
    from lexigram.auth.protocols import TokenValidatorProtocol
    from lexigram.auth.session.cookie_backend import SessionCookieBackend
    from lexigram.auth.storage.oauth_identity_store import (
        MongoDBOAuthIdentityStore,
        OAuthIdentity,
        OAuthIdentityStore,
        SQLAlchemyOAuthIdentityStore,
    )
    from lexigram.auth.types import (
        AuthResult,
        AuthStatus,
        RoleDefinition,
        UserStatus,
    )
    from lexigram.contracts.auth import (
        IdentityResolverProtocol,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Session cookie backend
    "SessionCookieBackend": (
        "lexigram.auth.session.cookie_backend",
        "SessionCookieBackend",
    ),
    # Module
    "AuthModule": ("lexigram.auth.module", "AuthModule"),
    # Config
    "AuthConfig": ("lexigram.auth.config", "AuthConfig"),
    "JWTConfig": ("lexigram.auth.config", "JWTConfig"),
    "MFAConfig": ("lexigram.auth.config", "MFAConfig"),
    "RBACConfig": ("lexigram.auth.config", "RBACConfig"),
    # Providers
    "AuthBundleProvider": ("lexigram.auth.di.bundle_provider", "AuthBundleProvider"),
    "AuthenticationProvider": ("lexigram.auth.di", "AuthenticationProvider"),
    "AuthorizationProvider": ("lexigram.auth.di", "AuthorizationProvider"),
    "GoogleOAuthProvider": ("lexigram.auth.di", "GoogleOAuthProvider"),
    # Services
    "AuthenticationService": ("lexigram.auth.authn.services", "AuthenticationService"),
    "LoginAttemptTracker": ("lexigram.auth.authn.services", "LoginAttemptTracker"),
    "LockoutConfig": ("lexigram.auth.authn.services", "LockoutConfig"),
    "UserService": ("lexigram.auth.authn.user_service", "UserService"),
    # API Key AuthenticatorProtocol
    "APIKeyAuthenticator": ("lexigram.auth.authn.api_key", "APIKeyAuthenticator"),
    "APIKeyConfig": ("lexigram.auth.authn.api_key", "APIKeyConfig"),
    # Core Security
    "JWTTokenManager": ("lexigram.auth.authn.jwt", "JWTTokenManager"),
    "GoogleOAuthService": ("lexigram.auth.authn.google_oauth", "GoogleOAuthService"),
    "PasswordHasher": ("lexigram.auth.authn.security", "PasswordHasher"),
    "PasswordPolicy": ("lexigram.auth.authn.security", "PasswordPolicy"),
    # Token Revocation
    "PersistentTokenRevocationStore": (
        "lexigram.auth.authn.revocation",
        "PersistentTokenRevocationStore",
    ),
    # Types
    "User": ("lexigram.auth.models", "User"),
    "AuthToken": ("lexigram.auth.models", "AuthToken"),
    "AuthResult": ("lexigram.auth.types", "AuthResult"),
    "AuthStatus": ("lexigram.auth.types", "AuthStatus"),
    "UserStatus": ("lexigram.auth.types", "UserStatus"),
    "RoleDefinition": ("lexigram.auth.types", "RoleDefinition"),
    # OAuth Identity Store
    "OAuthIdentityStore": (
        "lexigram.auth.storage.oauth_identity_store",
        "OAuthIdentityStore",
    ),
    "OAuthIdentity": ("lexigram.auth.storage.oauth_identity_store", "OAuthIdentity"),
    "SQLAlchemyOAuthIdentityStore": (
        "lexigram.auth.storage.oauth_identity_store",
        "SQLAlchemyOAuthIdentityStore",
    ),
    "MongoDBOAuthIdentityStore": (
        "lexigram.auth.storage.oauth_identity_store",
        "MongoDBOAuthIdentityStore",
    ),
    # Protocols
    "IdentityResolverProtocol": (
        "lexigram.contracts.auth",
        "IdentityResolverProtocol",
    ),
    "OAuthIdentityStoreProtocol": (
        "lexigram.contracts.auth",
        "OAuthIdentityStoreProtocol",
    ),
    "TokenValidatorProtocol": (
        "lexigram.auth.protocols",
        "TokenValidatorProtocol",
    ),
    # Exceptions (all from single canonical exceptions.py)
    "AuthError": ("lexigram.auth.exceptions", "AuthError"),
    "AuthenticationError": ("lexigram.auth.exceptions", "AuthenticationError"),
    "AuthorizationError": ("lexigram.auth.exceptions", "AuthorizationError"),
    "TokenError": ("lexigram.auth.exceptions", "TokenError"),
    "InvalidTokenError": ("lexigram.auth.exceptions", "InvalidTokenError"),
    "TokenExpiredError": ("lexigram.auth.exceptions", "TokenExpiredError"),
    # Leaf token/verification exceptions (merged from former errors.py)
    "AlreadyVerifiedError": ("lexigram.auth.exceptions", "AlreadyVerifiedError"),
    "TokenAudienceError": ("lexigram.auth.exceptions", "TokenAudienceError"),
    "TokenBlacklistedError": ("lexigram.auth.exceptions", "TokenBlacklistedError"),
    "TokenExpiredVerificationError": (
        "lexigram.auth.exceptions",
        "TokenExpiredVerificationError",
    ),
    "TokenInvalidError": ("lexigram.auth.exceptions", "TokenInvalidError"),
    "TokenNotFoundError": ("lexigram.auth.exceptions", "TokenNotFoundError"),
    "VerificationError": ("lexigram.auth.exceptions", "VerificationError"),
    # Guards & Dependencies
    "require_auth": ("lexigram.auth.authz.guards", "require_auth"),
    "require_roles": ("lexigram.auth.authz.guards", "require_roles"),
    "require_permissions": ("lexigram.auth.authz.guards", "require_permissions"),
    "optional_auth": ("lexigram.auth.authz.guards", "optional_auth"),
    # Domain Events
    "AuthenticationFailed": ("lexigram.auth.events", "AuthenticationFailed"),
    "PasswordChanged": ("lexigram.auth.events", "PasswordChanged"),
    "SessionCreated": ("lexigram.auth.events", "SessionCreated"),
    "SessionRevoked": ("lexigram.auth.events", "SessionRevoked"),
    "TokenRevoked": ("lexigram.auth.events", "TokenRevoked"),
    "UserAuthenticated": ("lexigram.auth.events", "UserAuthenticated"),
    "UserLoggedIn": ("lexigram.auth.events", "UserLoggedIn"),
    "UserLoggedOut": ("lexigram.auth.events", "UserLoggedOut"),
    "UserLoginFailed": ("lexigram.auth.events", "UserLoginFailed"),
    "UserLockedOut": ("lexigram.auth.events", "UserLockedOut"),
    "UserRegistered": ("lexigram.auth.events", "UserRegistered"),
    # Hooks
    "AuthAuthenticationFailedHook": (
        "lexigram.auth.hooks",
        "AuthAuthenticationFailedHook",
    ),
    "AuthTokenIssuedHook": ("lexigram.auth.hooks", "AuthTokenIssuedHook"),
    "AuthTokenRefreshedHook": ("lexigram.auth.hooks", "AuthTokenRefreshedHook"),
    "AuthTokenRevokedHook": ("lexigram.auth.hooks", "AuthTokenRevokedHook"),
    "AuthUserAuthenticatedHook": ("lexigram.auth.hooks", "AuthUserAuthenticatedHook"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for IDE support."""
    return list(__all__) + list(_LAZY_IMPORTS.keys())


__all__ = [
    "APIKeyAuthenticator",
    "APIKeyConfig",
    "AlreadyVerifiedError",
    "AuthAuthenticationFailedHook",
    "AuthBundleProvider",
    "AuthConfig",
    "AuthError",
    "AuthModule",
    "AuthResult",
    "AuthStatus",
    "AuthToken",
    "AuthTokenIssuedHook",
    "AuthTokenRefreshedHook",
    "AuthTokenRevokedHook",
    "AuthUserAuthenticatedHook",
    "AuthenticationFailed",
    "AuthenticationProvider",
    "AuthenticationService",
    "AuthorizationError",
    "AuthorizationProvider",
    "GoogleOAuthProvider",
    "GoogleOAuthService",
    "IdentityResolverProtocol",
    "InvalidTokenError",
    "JWTConfig",
    "JWTTokenManager",
    "LockoutConfig",
    "LoginAttemptTracker",
    "MFAConfig",
    "MongoDBOAuthIdentityStore",
    "OAuthIdentity",
    "OAuthIdentityStore",
    "PasswordChanged",
    "PasswordHasher",
    "PasswordPolicy",
    "PersistentTokenRevocationStore",
    "RBACConfig",
    "RoleDefinition",
    "SQLAlchemyOAuthIdentityStore",
    "SessionCookieBackend",
    "SessionCreated",
    "SessionRevoked",
    "TokenAudienceError",
    "TokenBlacklistedError",
    "TokenError",
    "TokenExpiredError",
    "TokenExpiredVerificationError",
    "TokenInvalidError",
    "TokenNotFoundError",
    "TokenRevoked",
    "TokenValidatorProtocol",
    "User",
    "UserAuthenticated",
    "UserLockedOut",
    "UserLoggedIn",
    "UserLoggedOut",
    "UserLoginFailed",
    "UserRegistered",
    "UserService",
    "UserStatus",
    "VerificationError",
    "optional_auth",
    "require_auth",
    "require_permissions",
    "require_roles",
]
