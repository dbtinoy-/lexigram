"""Debug mode utilities for Lexigram Framework lifecycle logging.

The ``LEX_DEBUG`` environment variable corresponds to the ``debug``
field in :class:`~lexigram.config.main.LexigramConfig`. This module reads
it directly for early-boot usage before the config system has been
initialized. At runtime, ``LexigramConfig.debug`` is the canonical source.
"""

from __future__ import annotations

import os
from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)


def is_debug_mode() -> bool:
    """Check if Lexigram debug mode is enabled.

    Reads the ``LEX_DEBUG`` env var directly so this function works
    at early-boot time before config is loaded. The env var corresponds to
    ``LexigramConfig.debug`` and is set consistently by the config system.
    """
    return os.environ.get("LEX_DEBUG", "").strip() in ("1", "true", "yes")


def log_lifecycle(event: str, **context: Any) -> None:
    """Emit a structured lifecycle debug log."""
    if not is_debug_mode():
        return

    logger.debug(event, **context)


__all__ = ["is_debug_mode", "log_lifecycle"]
