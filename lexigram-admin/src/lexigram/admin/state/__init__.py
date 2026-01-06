"""State management for Lexigram Admin.

PEP 562 lazy loading to avoid import-time dependency issues.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.state.context import AdminContext
    from lexigram.admin.state.persistence import StatePersistenceManager
    from lexigram.admin.state.store import GlobalStore
    from lexigram.admin.state.url import URLState
    from lexigram.admin.state.url_sync import URLStateManager

_EXPORTS = {
    "AdminContext": "lexigram.admin.state.context",
    "URLState": "lexigram.admin.state.url",
    "URLStateManager": "lexigram.admin.state.url_sync",
    "GlobalStore": "lexigram.admin.state.store",
    "StatePersistenceManager": "lexigram.admin.state.persistence",
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        module = importlib.import_module(_EXPORTS[name], __package__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> Any:
    return __all__
