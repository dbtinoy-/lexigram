"""Exceptions for the core subsystem.

All exceptions derive from :class:`LexigramError` so they can be caught
uniformly at the framework level.
"""

from __future__ import annotations

from lexigram.contracts.exceptions import LexigramError


class CoreError(LexigramError):
    """Base exception for all core errors."""

    _code: str = "LEX_ERR_CORE_005"


__all__ = [
    "CoreError",
]
