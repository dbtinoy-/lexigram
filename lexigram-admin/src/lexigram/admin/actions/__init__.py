"""Action managers for Lexigram Admin.

PEP 562 lazy loading to avoid import-time dependency issues.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.actions.audited import AuditedAction
    from lexigram.admin.actions.bulk_manager import (
        BulkActionManager,
        BulkActionProgress,
        BulkActionResult,
        BulkActionSnapshot,
        BulkAssignConfig,
        BulkEditField,
        IBulkDataSource,
    )
    from lexigram.admin.actions.header_manager import (
        ColumnVisibilityConfig,
        DensityConfig,
        HeaderAction,
        HeaderActionManager,
        HeaderActionStyle,
        IHeaderDataSource,
        TableDensity,
    )
    from lexigram.admin.actions.polymorphic import PolymorphicBulkAction
    from lexigram.admin.actions.row_manager import (
        ActionGroup,
        ActionPosition,
        ActionStyle,
        IRowDataSource,
        RowAction,
        RowActionManager,
    )

_EXPORTS = {
    # audited
    "AuditedAction": "lexigram.admin.actions.audited",
    # polymorphic
    "PolymorphicBulkAction": "lexigram.admin.actions.polymorphic",
    # bulk_manager
    "IBulkDataSource": "lexigram.admin.actions.bulk_manager",
    "BulkEditField": "lexigram.admin.actions.bulk_manager",
    "BulkAssignConfig": "lexigram.admin.actions.bulk_manager",
    "BulkActionResult": "lexigram.admin.actions.bulk_manager",
    "BulkActionSnapshot": "lexigram.admin.actions.bulk_manager",
    "BulkActionProgress": "lexigram.admin.actions.bulk_manager",
    "BulkActionManager": "lexigram.admin.actions.bulk_manager",
    # header_manager
    "HeaderActionStyle": "lexigram.admin.actions.header_manager",
    "TableDensity": "lexigram.admin.actions.header_manager",
    "HeaderAction": "lexigram.admin.actions.header_manager",
    "ColumnVisibilityConfig": "lexigram.admin.actions.header_manager",
    "DensityConfig": "lexigram.admin.actions.header_manager",
    "IHeaderDataSource": "lexigram.admin.actions.header_manager",
    "HeaderActionManager": "lexigram.admin.actions.header_manager",
    # row_manager
    "ActionStyle": "lexigram.admin.actions.row_manager",
    "ActionPosition": "lexigram.admin.actions.row_manager",
    "RowAction": "lexigram.admin.actions.row_manager",
    "ActionGroup": "lexigram.admin.actions.row_manager",
    "IRowDataSource": "lexigram.admin.actions.row_manager",
    "RowActionManager": "lexigram.admin.actions.row_manager",
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
