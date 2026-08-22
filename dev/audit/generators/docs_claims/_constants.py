"""Constants for the docs-claims audit."""

from __future__ import annotations

import re

_ENV_TOKEN_RE = re.compile(r"\bLEX_[A-Z][A-Z0-9_]*\b")
_PRIORITY_RE = re.compile(r"ProviderPriority\.([A-Z][A-Z0-9_]*)")
_SECTION_CONFIG_SUFFIX = "Config"
# `LEX_ERR_*` is the error-code namespace (LEX_ERR_<PKG>_<CODE>) — not env vars.
_ERROR_CODE_PREFIX = "LEX_ERR_"
# Trailing-delimiter tokens (`LEX_X__`) are env-source prefix claims.
_PREFIX_TOKEN_SUFFIX = "__"

# Env vars read directly by framework code (never a section/key mapping).
_DIRECT_READ_ENV_VARS = frozenset(
    {
        "LEX_CONFIG",
        "LEX_DEBUG",
        "LEX_ENV",
        "LEX_PROFILE",
        "LEX_QUIET",
    }
)

# Dynamic namespaces: any token under these prefixes is a valid env var.
_DYNAMIC_PREFIXES = (
    # Feature-flag overrides: FeatureFlagsConfig.flag_env_prefix is "LEX_FLAG_".
    "LEX_FLAG_",
)

_PRIORITY_MODULE = "lexigram.contracts.core.provider"
_PRIORITY_ENUM = "ProviderPriority"
