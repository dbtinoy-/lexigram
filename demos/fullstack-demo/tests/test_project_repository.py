import os
import subprocess
import tempfile

import pytest
from lexigram.sql.providers.database_service import DatabaseService

from shorts_creator.models.project import Project
from shorts_creator.repositories.project_repository import ProjectRepository

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
async def repo():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    if path.startswith("/"):
        db_url = f"sqlite:////{path.lstrip('/')}"
        alembic_url = f"sqlite+aiosqlite:////{path.lstrip('/')}"
    else:
        db_url = f"sqlite:///{path}"
        alembic_url = f"sqlite+aiosqlite:///{path}"
    subprocess.run(
        ["alembic", "-c", "migrations/primary/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, "SHORTS_CREATOR_DATABASE_URL": alembic_url},
        check=True,
        capture_output=True,
    )
    service = DatabaseService(db_url)
    await service.connect()
    yield ProjectRepository(service)
    await service.disconnect()
    os.unlink(path)


class TestProjectRepository:
    async def test_create_and_get(self, repo):
        p = Project(id="p1", topic="self_improvement", focus="habits", title="My Campaign")
        created = await repo.create(p)
        assert created.id == "p1"
        found = await repo.get("p1")
        assert found is not None
        assert found.topic == "self_improvement"
        assert found.title == "My Campaign"

    async def test_update_title(self, repo):
        p = Project(id="p2", topic="psychology", title="Old Title")
        await repo.create(p)
        p.title = "New Title"
        await repo.update(p)
        found = await repo.get("p2")
        assert found.title == "New Title"

    async def test_get_missing_returns_none(self, repo):
        assert await repo.get("nonexistent") is None
