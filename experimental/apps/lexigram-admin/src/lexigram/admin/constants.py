"""Package-level constants for lexigram-admin.

These are stable, typed constants used across the Admin package.
Import from here — never hard-code these values elsewhere.
"""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-admin")
except ImportError:
    __version__ = "0.0.0"


# ---------------------------------------------------------------------------
# Environment variable prefix
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_ADMIN__"
ENV_NESTED_DELIMITER: str = "__"
"""Delimiter for nested env var keys (e.g. LEX_ADMIN__AUTH__SESSION_SECRET)."""

# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------

DEFAULT_ADMIN_PATH: str = "/admin"
DEFAULT_ITEMS_PER_PAGE: int = 25
DEFAULT_MAX_ITEMS_PER_PAGE: int = 200
DEFAULT_SEARCH_LIMIT: int = 50
DEFAULT_SESSION_LIFETIME: int = 86400  # 24 hours in seconds

# ---------------------------------------------------------------------------
# Permission constants
# ---------------------------------------------------------------------------

PERMISSION_VIEW: str = "view"
PERMISSION_CREATE: str = "create"
PERMISSION_EDIT: str = "edit"
PERMISSION_DELETE: str = "delete"
PERMISSION_ADMIN: str = "admin"

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

LAYOUT_SIDEBAR: str = "sidebar"
LAYOUT_TOP_NAV: str = "top_nav"

# ---------------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------------

THEME_LIGHT: str = "light"
THEME_DARK: str = "dark"
THEME_SYSTEM: str = "system"


__all__ = [
    "DEFAULT_ADMIN_PATH",
    "DEFAULT_ITEMS_PER_PAGE",
    "DEFAULT_MAX_ITEMS_PER_PAGE",
    "DEFAULT_SEARCH_LIMIT",
    "DEFAULT_SESSION_LIFETIME",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "LAYOUT_SIDEBAR",
    "LAYOUT_TOP_NAV",
    "PERMISSION_ADMIN",
    "PERMISSION_CREATE",
    "PERMISSION_DELETE",
    "PERMISSION_EDIT",
    "PERMISSION_VIEW",
    "THEME_DARK",
    "THEME_LIGHT",
    "THEME_SYSTEM",
    "__version__",
]
