"""Background tasks for Lexigram Admin.

PEP 562 lazy loading to avoid import-time dependency issues.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.tasks.bulk_operations import (
        AdminTaskResult,
        AdminTaskType,
        TaskProgress,
    )

_EXPORTS = {
    "AdminTaskType": ".bulk_operations",
    "TaskProgress": ".bulk_operations",
    "AdminTaskResult": ".bulk_operations",
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
