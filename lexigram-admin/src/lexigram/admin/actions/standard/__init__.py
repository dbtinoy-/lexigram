"""Standard action implementations for lexigram-admin.

Provides ready-to-use :class:`~lexigram.admin.actions.base.RowAction`,
:class:`~lexigram.admin.actions.base.BulkAction`, and
:class:`~lexigram.admin.actions.base.HeaderAction` subclasses that wrap
common data-source operations such as edit, view, delete, create, and
bulk delete. Each action comes with sensible defaults for name, label,
icon, and color.

Class implementations live in sibling modules grouped by action family
(``row``, ``bulk``, ``header``, ``export``, ``imports``).
"""

from __future__ import annotations

from lexigram.admin.actions.standard.bulk import (
    DeleteBulkAction,
    PurgeBulkAction,
    RestoreBulkAction,
)
from lexigram.admin.actions.standard.export import ExportAction, ExportBulkAction
from lexigram.admin.actions.standard.header import CreateAction
from lexigram.admin.actions.standard.imports import ImportAction, ImportBulkAction
from lexigram.admin.actions.standard.row import (
    CloneAction,
    DeleteAction,
    EditAction,
    PermissionsAction,
    PurgeAction,
    RestoreAction,
    ViewAction,
)

__all__ = [
    "CloneAction",
    "CreateAction",
    "DeleteAction",
    "DeleteBulkAction",
    "EditAction",
    "ExportAction",
    "ExportBulkAction",
    "ImportAction",
    "ImportBulkAction",
    "PurgeAction",
    "PurgeBulkAction",
    "RestoreAction",
    "RestoreBulkAction",
    "ViewAction",
]
