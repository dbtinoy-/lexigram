"""Services — business logic with Result[T, E] error handling.

Services live between controllers and repositories.  They implement
business rules and return Result types instead of raising exceptions.
"""

from __future__ import annotations

from taskapp.services.projects import ProjectService
from taskapp.services.tasks import TaskService
from taskapp.services.users import UserService

__all__ = ["ProjectService", "TaskService", "UserService"]
