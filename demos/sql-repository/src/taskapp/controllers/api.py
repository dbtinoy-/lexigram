"""Tasks API — HTTP surface for task management.

Controllers are thin: they validate input, call a service, and
return a response dict.  No business logic lives here.

Convention followed: **Controller pattern** — each handler resolves its
dependencies from the container and returns domain ``Result`` values.
The framework's result bridge serializes them.

Exposes the task manager over HTTP:

- ``GET /api/tasks/users``       — list users
- ``POST /api/tasks/users``      — create user
- ``GET /api/tasks/projects``    — list projects
- ``POST /api/tasks/projects``   — create project
- ``GET /api/tasks/tasks``       — list tasks
- ``POST /api/tasks/tasks``      — create task
- ``PUT /api/tasks/tasks/{id}/status`` — update task status
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, delete, get, post, put


class TasksApiController(Controller):
    """HTTP surface for task management.

    Delegates to in-memory stores for business logic.  Returns dicts
    that the framework serialises to JSON.

    The controller receives its stores via constructor injection —
    the provider wires them during ``boot()``.
    """

    prefix = "/api/tasks"

    def __init__(
        self,
        users_store: dict[int, dict[str, Any]] | None = None,
        projects_store: dict[int, dict[str, Any]] | None = None,
        tasks_store: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self._users = users_store or {}
        self._projects = projects_store or {}
        self._tasks = tasks_store or {}
        self._next_user_id = max(self._users.keys(), default=0) + 1
        self._next_project_id = max(self._projects.keys(), default=0) + 1
        self._next_task_id = max(self._tasks.keys(), default=0) + 1

    # ── Users ─────────────────────────────────────────────────────────────
    # User management endpoints — CRUD operations on the users store.
    # In production, replace with a repository pattern:
    #   user = await self._users_repo.create(UserCreate(**body))
    # ─────────────────────────────────────────────────────────────────────

    @post("/users")
    async def create_user(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create a new user.

        Body: ``{"name": "Alice", "email": "alice@example.com", "role": "admin"}``

        Returns:
            ``{"user": {"id": 1, "name": "Alice", ...}}``
        """
        name = body.get("name", "")
        email = body.get("email", "")
        if not name:
            return {"error": "Name is required"}
        if not email:
            return {"error": "Email is required"}

        user_id = self._next_user_id
        self._next_user_id += 1
        user = {
            "id": user_id,
            "name": name,
            "email": email,
            "role": body.get("role", "member"),
        }
        self._users[user_id] = user
        return {"user": user}

    @get("/users")
    async def list_users(self) -> list[dict[str, Any]]:
        """List all users."""
        return list(self._users.values())

    @get("/users/{user_id}")
    async def get_user(self, user_id: int) -> dict[str, Any]:
        """Get a user by ID."""
        user = self._users.get(user_id)
        if user is None:
            return {"error": f"User {user_id} not found"}
        return {"user": user}

    @delete("/users/{user_id}")
    async def delete_user(self, user_id: int) -> dict[str, Any]:
        """Delete a user by ID."""
        if user_id not in self._users:
            return {"error": f"User {user_id} not found"}
        del self._users[user_id]
        return {"deleted": True}

    # ── Projects ──────────────────────────────────────────────────────────
    # Project management endpoints — CRUD operations on the projects store.
    # Projects are owned by users and contain tasks.
    # ─────────────────────────────────────────────────────────────────────

    @post("/projects")
    async def create_project(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create a new project.

        Body: ``{"name": "Website", "owner_id": 1}``

        Returns:
            ``{"project": {"id": 1, "name": "Website", ...}}``
        """
        name = body.get("name", "")
        owner_id = body.get("owner_id", 0)
        if not name:
            return {"error": "Project name is required"}
        if not owner_id:
            return {"error": "Owner ID is required"}

        project_id = self._next_project_id
        self._next_project_id += 1
        project = {
            "id": project_id,
            "name": name,
            "owner_id": owner_id,
            "status": "active",
        }
        self._projects[project_id] = project
        return {"project": project}

    @get("/projects")
    async def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        return list(self._projects.values())

    @get("/projects/{project_id}")
    async def get_project(self, project_id: int) -> dict[str, Any]:
        """Get a project by ID."""
        project = self._projects.get(project_id)
        if project is None:
            return {"error": f"Project {project_id} not found"}
        return {"project": project}

    @delete("/projects/{project_id}")
    async def delete_project(self, project_id: int) -> dict[str, Any]:
        """Delete a project by ID."""
        if project_id not in self._projects:
            return {"error": f"Project {project_id} not found"}
        del self._projects[project_id]
        return {"deleted": True}

    # ── Tasks ─────────────────────────────────────────────────────────────
    # Task management endpoints — CRUD operations on the tasks store.
    # Tasks belong to projects and can be assigned to users.
    # ─────────────────────────────────────────────────────────────────────

    @post("/tasks")
    async def create_task(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create a new task.

        Body: ``{"title": "Design homepage", "project_id": 1, "assignee_id": 1}``

        Returns:
            ``{"task": {"id": 1, "title": "Design homepage", ...}}``
        """
        title = body.get("title", "")
        project_id = body.get("project_id", 0)
        if not title:
            return {"error": "Task title is required"}
        if not project_id:
            return {"error": "Project ID is required"}

        task_id = self._next_task_id
        self._next_task_id += 1
        task = {
            "id": task_id,
            "title": title,
            "project_id": project_id,
            "assignee_id": body.get("assignee_id"),
            "status": "todo",
            "priority": body.get("priority", 0),
        }
        self._tasks[task_id] = task
        return {"task": task}

    @get("/tasks")
    async def list_tasks(self) -> list[dict[str, Any]]:
        """List all tasks."""
        return list(self._tasks.values())

    @get("/tasks/{task_id}")
    async def get_task(self, task_id: int) -> dict[str, Any]:
        """Get a task by ID."""
        task = self._tasks.get(task_id)
        if task is None:
            return {"error": f"Task {task_id} not found"}
        return {"task": task}

    @put("/tasks/{task_id}/status")
    async def update_task_status(
        self, task_id: int, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a task's status.

        Body: ``{"status": "in_progress"}``

        Valid statuses: ``todo``, ``in_progress``, ``done``
        """
        task = self._tasks.get(task_id)
        if task is None:
            return {"error": f"Task {task_id} not found"}

        status = body.get("status", "todo")
        valid_statuses = {"todo", "in_progress", "done"}
        if status not in valid_statuses:
            return {
                "error": f"Invalid status: {status}. Must be one of: {valid_statuses}"
            }

        task["status"] = status
        return {"task": task}

    @delete("/tasks/{task_id}")
    async def delete_task(self, task_id: int) -> dict[str, Any]:
        """Delete a task by ID."""
        if task_id not in self._tasks:
            return {"error": f"Task {task_id} not found"}
        del self._tasks[task_id]
        return {"deleted": True}


__all__ = ["TasksApiController"]
