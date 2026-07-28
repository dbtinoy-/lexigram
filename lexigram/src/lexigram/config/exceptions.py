"""Exceptions for the config subsystem.

Re-exports the canonical ``ConfigurationError`` from contracts and
defines common subtypes for specific config-loading failure scenarios.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.config import (
    ConfigurationError as ConfigurationError,
)


class ConfigSourceError(ConfigurationError):
    """Raised when a configuration source fails to load its values."""

    _code: str = "LEX_ERR_CFG_003"


class ConfigReloadError(ConfigurationError):
    """Raised when a live-reload attempt fails."""

    _code: str = "LEX_ERR_CFG_004"


class ConfigSectionNotFoundError(ConfigurationError):
    """Raised when a required config section is absent from the loaded config."""

    _code: str = "LEX_ERR_CFG_005"


__all__ = [
    "ConfigReloadError",
    "ConfigSectionNotFoundError",
    "ConfigSourceError",
    "ConfigurationError",
]
