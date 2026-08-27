"""Tests — real composition root, no mocks.

Every test boots a real Application with the actual DI container.
Services are tested through their public API, not by mocking internals.
"""

from __future__ import annotations

import pytest
import httpx


class TestAPI:
    """Test HTTP endpoints through the real composition root."""

    @pytest.mark.asyncio
    async def test_list_users(self, client: httpx.AsyncClient) -> None:
        """GET /api/tasks/users returns user list."""
        resp = await client.get("/api/tasks/users")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_create_and_get_user(self, client: httpx.AsyncClient) -> None:
        """POST + GET user flow."""
        resp = await client.post(
            "/api/tasks/users",
            json={"name": "Eve", "email": "eve@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert data["user"]["name"] == "Eve"

    @pytest.mark.asyncio
    async def test_create_user_validation(self, client: httpx.AsyncClient) -> None:
        """Empty name returns an error."""
        resp = await client.post(
            "/api/tasks/users",
            json={"name": "", "email": "test@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_list_projects(self, client: httpx.AsyncClient) -> None:
        """GET /api/tasks/projects returns project list."""
        resp = await client.get("/api/tasks/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_create_project(self, client: httpx.AsyncClient) -> None:
        """POST project creates a new project."""
        resp = await client.post(
            "/api/tasks/projects",
            json={"name": "New Feature", "owner_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "project" in data
        assert data["project"]["name"] == "New Feature"

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: httpx.AsyncClient) -> None:
        """GET /api/tasks/tasks returns task list."""
        resp = await client.get("/api/tasks/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_create_task(self, client: httpx.AsyncClient) -> None:
        """POST task creates a new task."""
        resp = await client.post(
            "/api/tasks/tasks",
            json={"title": "New task", "project_id": 1, "assignee_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task" in data
        assert data["task"]["title"] == "New task"

    @pytest.mark.asyncio
    async def test_update_task_status(self, client: httpx.AsyncClient) -> None:
        """PUT task status updates the task."""
        resp = await client.put(
            "/api/tasks/tasks/1/status",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task" in data
        assert data["task"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_task_status_invalid(self, client: httpx.AsyncClient) -> None:
        """Invalid status returns an error."""
        resp = await client.put(
            "/api/tasks/tasks/1/status",
            json={"status": "invalid"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_delete_task(self, client: httpx.AsyncClient) -> None:
        """DELETE task removes the task."""
        resp = await client.delete("/api/tasks/tasks/3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
