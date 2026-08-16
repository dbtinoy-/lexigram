"""Migration package for NoSQL schema management."""

from __future__ import annotations

from lexigram.nosql.migration.manager import MigrationManager, MigrationRecord
from lexigram.nosql.migration.operations import (
    AddField,
    CreateIndex,
    DropCollection,
    DropIndex,
    RenameField,
)

__all__ = [
    "AddField",
    "CreateIndex",
    "DropCollection",
    "DropIndex",
    "MigrationManager",
    "MigrationRecord",
    "RenameField",
]
