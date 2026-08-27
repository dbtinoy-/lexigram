"""Project service — business logic for project management."""

from __future__ import annotations

from typing import Any

from lexigram.result import Result
from taskapp.domain import Project, ProjectStatus


class ProjectService:
    """Business operations for projects."""

    def __init__(self, project_repo: Any) -> None:
        self._repo = project_repo

    async def create_project(
        self,
        name: str,
        owner_id: int,
    ) -> Result[Project, str]:
        """Create a new project."""
        if not name:
            return Result.err("Project name is required")
        if owner_id <= 0:
            return Result.err("Valid owner ID is required")

        project = Project(name=name, owner_id=owner_id)
        created = await self._repo.add(project)
        return Result.ok(created)

    async def get_project(self, project_id: int) -> Result[Project, str]:
        """Get a project by ID."""
        project = await self._repo.get(project_id)
        if project is None:
            return Result.err(f"Project {project_id} not found")
        return Result.ok(project)

    async def list_projects(self) -> list[Project]:
        """List all active projects."""
        return await self._repo.list()

    async def archive_project(self, project_id: int) -> Result[Project, str]:
        """Archive a project (soft delete)."""
        project = await self._repo.get(project_id)
        if project is None:
            return Result.err(f"Project {project_id} not found")

        archived = Project(
            id=project.id,
            name=project.name,
            owner_id=project.owner_id,
            status=ProjectStatus.ARCHIVED,
        )
        updated = await self._repo.update(project_id, archived)
        return Result.ok(updated)

    async def delete_project(self, project_id: int) -> Result[bool, str]:
        """Delete a project by ID."""
        deleted = await self._repo.delete(project_id)
        if not deleted:
            return Result.err(f"Project {project_id} not found")
        return Result.ok(True)


__all__ = ["ProjectService"]
