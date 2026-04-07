"""Constants for the lexigram-secrets package."""

from __future__ import annotations

__version__ = "0.1.0"

ENV_PREFIX = "LEX_SECRETS_"
ENV_NESTED_DELIMITER = "__"

DEFAULT_BACKEND_TYPE = "memory"
DEFAULT_MAX_AGE_SECONDS = 7776000.0
DEFAULT_WARNING_BEFORE_SECONDS = 86400.0
DEFAULT_AUDIT_ACTOR_ID = "secrets-system"

DEFAULT_VAULT_URL = "http://127.0.0.1:8200"
DEFAULT_VAULT_MOUNT_POINT = "secret"

ERROR_UNKNOWN_BACKEND = "Unknown backend_type: {backend!r}"
