"""Feature flag manager package.

Re-exports :class:`FlagManager`, :class:`ManagerConfig`, and the listener
type aliases from their respective submodules.
"""

from __future__ import annotations

from lexigram.features.manager.config import ManagerConfig
from lexigram.features.manager.flag_manager import FlagAuditEntry, FlagManager
from lexigram.features.manager.types import AsyncFlagChangeListener, FlagChangeListener

__all__ = [
    "AsyncFlagChangeListener",
    "FlagAuditEntry",
    "FlagChangeListener",
    "FlagManager",
    "ManagerConfig",
]
