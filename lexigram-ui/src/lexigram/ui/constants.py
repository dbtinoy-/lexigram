"""UI package constants and enums."""

from __future__ import annotations

from enum import StrEnum
import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ui")
except ImportError:
    __version__ = "0.0.0"


ENV_PREFIX: str = "LEX_UI__"
ENV_NESTED_DELIMITER: str = "__"


class UITheme(StrEnum):
    """Available UI themes."""

    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


class Breakpoint(StrEnum):
    """Responsive design breakpoints."""

    SM = "640px"
    MD = "768px"
    LG = "1024px"
    XL = "1280px"
    XXL = "1536px"


UI_CSP_REQUIREMENTS: dict[str, set[str]] = {
    "script-src": {
        "https://unpkg.com",
        "https://cdn.jsdelivr.net",
        "https://cdn.tailwindcss.com",
    },
    "style-src": {
        "https://cdn.jsdelivr.net",
        "https://cdn.tailwindcss.com",
        "https://unpkg.com",
    },
    "connect-src": {
        "https://unpkg.com",
    },
}

__all__ = [
    "Breakpoint",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "UITheme",
    "UI_CSP_REQUIREMENTS",
    "__version__",
]
