"""Domain models — immutable value objects for the task management domain.

These are plain dataclasses, NOT ORM models.  The repository handles
the mapping between domain entities and database rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TaskStatus(StrEnum):
    """Task lifecycle states."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class ProjectStatus(StrEnum):
    """Project lifecycle states."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class UserRole(StrEnum):
    """User roles for RBAC."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


@dataclass(frozen=True)
class User:
    """A user in the system."""

    id: int | None = None
    name: str = ""
    email: str = ""
    role: UserRole = UserRole.MEMBER


@dataclass(frozen=True)
class Project:
    """A project that groups tasks."""

    id: int | None = None
    name: str = ""
    owner_id: int | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE


@dataclass(frozen=True)
class Task:
    """A task within a project."""

    id: int | None = None
    title: str = ""
    project_id: int | None = None
    assignee_id: int | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = 0


__all__ = [
    "Project",
    "ProjectStatus",
    "Task",
    "TaskStatus",
    "User",
    "UserRole",
]
