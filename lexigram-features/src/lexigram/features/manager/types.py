"""FlagChangeListener and AsyncFlagChangeListener type aliases.

These are defined separately so that :mod:`lexigram.features.manager.flag_manager`
can import them without circular dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

# Signature: (flag_name, old_enabled, new_enabled)
FlagChangeListener = Callable[[str, bool, bool], None]

# Async variant — same signature but returns a coroutine.
AsyncFlagChangeListener = Callable[[str, bool, bool], Coroutine[Any, Any, None]]

__all__ = ["AsyncFlagChangeListener", "FlagChangeListener"]
