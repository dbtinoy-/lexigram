"""Constants for lexigram-auth."""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__ = importlib.metadata.version("lexigram-auth")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

# -- Environment Variable Prefixes -------------------------------------------

ENV_PREFIX: str = "LEX_AUTH__"
ENV_NESTED_DELIMITER: str = "__"

# -- Token Defaults ----------------------------------------------------------

DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
DEFAULT_TOKEN_ALGORITHM: str = "HS256"
DEFAULT_TOKEN_TYPE: str = "Bearer"

# Grace period (seconds) during which tokens signed by a rotated-out key
# remain accepted. Prevents immediate user logout on rotation.
DEFAULT_JWT_KEY_ROTATION_GRACE_PERIOD_SECONDS: int = 3600

# -- Password Policy Defaults ------------------------------------------------

DEFAULT_MIN_PASSWORD_LENGTH: int = 8
DEFAULT_MAX_PASSWORD_LENGTH: int = 128
DEFAULT_PASSWORD_HASH_ROUNDS: int = 12

# -- Session Defaults --------------------------------------------------------

DEFAULT_SESSION_TIMEOUT_MINUTES: int = 60
DEFAULT_SESSION_COOKIE_NAME: str = "session"
DEFAULT_SESSION_COOKIE_SECURE: bool = True
DEFAULT_SESSION_COOKIE_HTTPONLY: bool = True

# -- MFA Defaults ------------------------------------------------------------

DEFAULT_TOTP_DIGITS: int = 6
DEFAULT_TOTP_INTERVAL: int = 30
DEFAULT_TOTP_VALID_WINDOW: int = 1

__all__ = [
    "DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "DEFAULT_JWT_KEY_ROTATION_GRACE_PERIOD_SECONDS",
    "DEFAULT_MAX_PASSWORD_LENGTH",
    "DEFAULT_MIN_PASSWORD_LENGTH",
    "DEFAULT_PASSWORD_HASH_ROUNDS",
    "DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS",
    "DEFAULT_SESSION_COOKIE_HTTPONLY",
    "DEFAULT_SESSION_COOKIE_NAME",
    "DEFAULT_SESSION_COOKIE_SECURE",
    "DEFAULT_SESSION_TIMEOUT_MINUTES",
    "DEFAULT_TOKEN_ALGORITHM",
    "DEFAULT_TOKEN_TYPE",
    "DEFAULT_TOTP_DIGITS",
    "DEFAULT_TOTP_INTERVAL",
    "DEFAULT_TOTP_VALID_WINDOW",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]
