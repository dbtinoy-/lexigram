"""
Database provider implementations for the Hollow Interfaces architecture

These are the community edition implementations of the database provider protocols.

The module uses lazy imports for optional providers to avoid importing heavy
optional dependencies at package import time. Optional providers are loaded
on attribute access (PEP 562 __getattr__).
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from lexigram.sql.logging import (
    ConsoleQueryLogger,
    FileQueryLogger,
    MemoryQueryLogger,
    QueryLoggerBase,
)
from lexigram.sql.migrations.manager import SimpleMigrationManager
from lexigram.sql.pool.connection import AbstractConnectionPool, SimpleConnectionPool
from lexigram.sql.providers.base_provider import DatabaseDriver
from lexigram.sql.providers.database_service import DatabaseService
from lexigram.sql.providers.sqlite_provider import SQLiteProvider
from lexigram.sql.unit_of_work.simple import SimpleUnitOfWork, unit_of_work

# Export the core, always-available names
__all__ = [
    "AbstractConnectionPool",
    "ConsoleQueryLogger",
    "DatabaseDriver",
    "DatabaseService",
    "FileQueryLogger",
    "MemoryQueryLogger",
    "MySQLProvider",
    "PostgresProvider",
    "QueryLoggerBase",
    "SQLiteProvider",
    "SimpleConnectionPool",
    "unit_of_work",
]

from lexigram.sql.providers._lazy import _lazy_import


def __dir__() -> list[str]:
    return sorted(__all__)


def __getattr__(name: str) -> Any:  # PEP 562 module-level getattr
    # Defer to the lazy import map so we don't maintain parallel lists.
    try:
        return _lazy_import(name)
    except ImportError:
        raise AttributeError(name) from None
