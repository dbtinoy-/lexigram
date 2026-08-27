"""Repository implementations — map domain entities to database rows.

Each repository extends ``SQLRepository`` and implements the two abstract
methods: ``_entity_to_dict`` (domain → row) and ``_row_to_entity`` (row → domain).
"""

from __future__ import annotations

from taskapp.repository.projects import ProjectRepository
from taskapp.repository.tasks import TaskRepository
from taskapp.repository.users import UserRepository

__all__ = [
    "ProjectRepository",
    "TaskRepository",
    "UserRepository",
]
