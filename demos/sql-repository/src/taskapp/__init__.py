"""SQL repository demo — task management with in-memory stores.

Convention followed: **Package exports** — ``__init__.py`` re-exports
the public API surface without defining logic.

Exports:

- ``create_app`` — composition root for the application
- ``TaskAppConfig`` — demo configuration model
- ``TaskProvider`` — DI provider for task management services
"""

from __future__ import annotations

from taskapp.app import create_app
from taskapp.config import TaskAppConfig
from taskapp.di.provider import TaskProvider

__all__ = [
    "TaskAppConfig",
    "TaskProvider",
    "create_app",
]
