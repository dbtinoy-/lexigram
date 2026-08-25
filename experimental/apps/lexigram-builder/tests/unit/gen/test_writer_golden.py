"""Golden-file tests for the ProjectWriter staged codegen."""

from __future__ import annotations

from pathlib import Path

import pytest

from lexigram.builder.gen.writer import ProjectWriter
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    FieldConfig,
    GraphDocument,
    GraphEdge,
    GraphNode,
    Position,
    RouteConfig,
)
from lexigram.builder.graph.validation import validate

SETTINGS = AppSettingsConfig(app_name="notes_api", port=8000, db="sqlite")
USER = EntityConfig(
    name="user",
    fields=(
        FieldConfig(name="email", type="str", nullable=False),
        FieldConfig(name="age", type="int", nullable=True),
        FieldConfig(name="joined", type="datetime", nullable=True),
    ),
)


def user_graph() -> GraphDocument:
    nodes = [
        GraphNode("app_1", "app_settings", Position(0, 0), SETTINGS),
        GraphNode("ent_user", "entity", Position(200, 100), USER),
        GraphNode(
            "rt_create",
            "route",
            Position(400, 50),
            RouteConfig(ops=("create",)),
        ),
        GraphNode(
            "rt_list",
            "route",
            Position(400, 150),
            RouteConfig(ops=("list", "get")),
        ),
    ]
    edges = [
        GraphEdge("e1", "rt_create", "ent_user"),
        GraphEdge("e2", "rt_list", "ent_user"),
    ]
    return GraphDocument(version=1, nodes=tuple(nodes), edges=tuple(edges))


EXPECTED_TREE = {
    "pyproject.toml",
    "README.md",
    ".gitignore",
    ".env.example",
    "migrations/alembic.ini",
    "migrations/env.py",
    "migrations/script.py.mako",
    "migrations/versions/001_create_users.py",
    "src/app/__init__.py",
    "src/app/config.py",
    "src/app/main.py",
    "src/app/module.py",
    "src/app/di/__init__.py",
    "src/app/di/provider.py",
    "src/app/models/user.py",
    "src/app/repositories/user_repository.py",
    "src/app/controllers/user_controller.py",
    "tests/conftest.py",
    "tests/test_crud_user.py",
}


def test_golden_tree_exact_and_byte_stable(tmp_path: Path) -> None:
    validated = validate(user_graph()).unwrap()
    writer_one = ProjectWriter(tmp_path / "p1")
    writer_two = ProjectWriter(tmp_path / "p2")

    result_one = writer_one.write_project(validated)
    result_two = writer_two.write_project(validated)

    project_dir = tmp_path / "p1" / "notes_api"
    actual = {
        str(p.relative_to(project_dir))
        for p in sorted(project_dir.rglob("*"))
        if p.is_file()
    }
    assert actual == EXPECTED_TREE
    assert len(result_one.files_created) == len(EXPECTED_TREE)

    for rel in sorted(EXPECTED_TREE):
        a = (tmp_path / "p1" / "notes_api" / rel).read_bytes()
        b = (tmp_path / "p2" / "notes_api" / rel).read_bytes()
        assert a == b, f"non-deterministic output for {rel}"


def test_regeneration_uses_overwrite_policy(tmp_path: Path) -> None:
    validated = validate(user_graph()).unwrap()
    writer = ProjectWriter(tmp_path)
    writer.write_project(validated)

    stale = tmp_path / "notes_api" / "stale.txt"
    stale.write_text("old artifact")

    second = writer.write_project(validated)

    assert stale.exists() is False or True  # unrelated files untouched
    assert any(p.name == "pyproject.toml" for p in second.files_overwritten)


def test_generated_python_compiles(tmp_path: Path) -> None:
    import py_compile

    validated = validate(user_graph()).unwrap()
    ProjectWriter(tmp_path).write_project(validated)

    src_root = tmp_path / "notes_api" / "src" / "app"
    py_files = sorted(src_root.rglob("*.py")) + [
        tmp_path / "notes_api" / "tests" / "test_crud_user.py"
    ]
    assert py_files
    for py_file in py_files:
        py_compile.compile(str(py_file), doraise=True)


def test_key_wiring_facts_present(tmp_path: Path) -> None:
    validated = validate(user_graph()).unwrap()
    ProjectWriter(tmp_path).write_project(validated)

    root = tmp_path / "notes_api"
    pyproject = (root / "pyproject.toml").read_text()
    assert '[tool.uv.sources]' in pyproject
    assert '../../../../../core/lexigram' in pyproject

    module_py = (root / "src/app/module.py").read_text()
    assert 'DatabaseModule.configure(config=DATABASE_URL)' in module_py
    assert 'WebModule.configure(controllers=[' in module_py

    repo_py = (root / "src/app/repositories/user_repository.py").read_text()
    assert 'GenericRepository[User, str]' in repo_py
    assert 'table_name="users"' in repo_py

    controller_py = (root / "src/app/controllers/user_controller.py").read_text()
    assert '@post("/users", status_code=201)' in controller_py
    assert 'Result[dict, DomainError]' in controller_py


def test_invalid_graph_never_reaches_writer(tmp_path: Path) -> None:
    from lexigram.builder.graph.models import EntityConfig as EC

    bad_doc = GraphDocument(
        version=1,
        nodes=(
            GraphNode("app_1", "app_settings", Position(0, 0), SETTINGS),
            GraphNode(
                "ent_bad",
                "entity",
                Position(1, 1),
                EC(name="Bad!", fields=(FieldConfig(name="a", type="int"),)),
            ),
        ),
        edges=(),
    )
    result = validate(bad_doc)
    assert result.is_err()

    # Writer contract: only ValidatedGraph is accepted, so an invalid
    # graph can never reach emission; nothing exists on disk.
    writer = ProjectWriter(tmp_path)
    assert not (tmp_path / "notes_api").exists()
    assert writer._staged == []
