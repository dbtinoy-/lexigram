"""Tests for the fs-backed ProjectService."""

from __future__ import annotations

from pathlib import Path

from lexigram.builder.exceptions import (
    InvalidProjectNameError,
    ProjectNotFoundError,
)
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    FieldConfig,
    GraphDocument,
    GraphNode,
    Position,
)
from lexigram.builder.services.projects import ProjectService

SETTINGS = AppSettingsConfig(app_name="notes_api", port=8000, db="sqlite")


def settings_node() -> GraphNode:
    return GraphNode("app_1", "app_settings", Position(0, 0), SETTINGS)


def user_entity() -> GraphNode:
    return GraphNode(
        "ent_user",
        "entity",
        Position(10, 10),
        EntityConfig(name="user", fields=(FieldConfig(name="email", type="str"),)),
    )


def valid_doc() -> GraphDocument:
    return GraphDocument(version=1, nodes=(settings_node(), user_entity()), edges=())


class TestCreate:
    def test_creates_dir_and_fresh_graph(self, tmp_path: Path) -> None:
        svc = ProjectService(tmp_path / "projects")
        result = svc.create("notes_api")
        assert result.is_ok()
        assert (tmp_path / "projects" / "notes_api" / "graph.json").is_file()

    def test_rejects_bad_name(self, tmp_path: Path) -> None:
        svc = ProjectService(tmp_path)
        result = svc.create("BadName")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), InvalidProjectNameError)

    def test_duplicate_rejected(self, tmp_path: Path) -> None:
        svc = ProjectService(tmp_path)
        svc.create("alpha")
        assert svc.create("alpha").is_err()


class TestSaveLoadRoundtrip:
    def test_save_then_load_preserves_document(self, tmp_path: Path) -> None:
        svc = ProjectService(tmp_path)
        svc.create("notes_api")

        saved = svc.save_graph("notes_api", valid_doc())
        assert saved.is_ok()

        loaded = svc.load_graph("notes_api")
        assert loaded.is_ok()
        doc = loaded.unwrap()
        assert doc.version == 1
        assert {n.id for n in doc.nodes} == {"app_1", "ent_user"}
        entity = next(n for n in doc.nodes if n.kind == "entity")
        assert entity.config.fields[0].name == "email"  # type: ignore[union-attr]

    def test_load_validated_runs_rules(self, tmp_path: Path) -> None:
        svc = ProjectService(tmp_path)
        svc.create("notes_api")
        svc.save_graph("notes_api", valid_doc())

        validated = svc.load_validated("notes_api")
        assert validated.is_ok()

    def test_invalid_save_keeps_previous_file(self, tmp_path: Path) -> None:
        svc = ProjectService(tmp_path)
        svc.create("notes_api")
        svc.save_graph("notes_api", valid_doc())
        before = (tmp_path / "notes_api" / "graph.json").read_text()

        bad_entity = GraphNode(
            "ent_x",
            "entity",
            Position(5, 5),
            EntityConfig(name="Bad!", fields=(FieldConfig(name="a", type="int"),)),
        )
        broken = GraphDocument(version=1, nodes=(settings_node(), bad_entity), edges=())

        saved = svc.save_graph("notes_api", broken)

        assert saved.is_err()
        from lexigram.builder.exceptions import GraphValidationError

        err = saved.unwrap_err()
        assert isinstance(err, GraphValidationError)
        assert err.diagnostics
        after = (tmp_path / "notes_api" / "graph.json").read_text()
        assert after == before


def test_malformed_json_surfaces_err(tmp_path: Path) -> None:
    svc = ProjectService(tmp_path)
    svc.create("notes_api")
    graph = tmp_path / "notes_api" / "graph.json"
    graph.write_text("{ not json", encoding="utf-8")

    loaded = svc.load_graph("notes_api")
    assert loaded.is_err()


def test_delete_and_missing_cases(tmp_path: Path) -> None:
    svc = ProjectService(tmp_path)
    svc.create("alpha")
    assert svc.delete("alpha").is_ok()
    assert svc.delete("alpha").is_err()
    loaded = svc.load_graph("alpha")
    assert isinstance(loaded.unwrap_err(), ProjectNotFoundError)
