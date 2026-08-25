"""File-backed project store for canvas graphs."""

from __future__ import annotations

import json  # noqa: TID251 - stdlib json for graph.json (orjson overkill)
from pathlib import Path

from lexigram.builder.exceptions import (
    BuilderError,
    GraphValidationError,
    InvalidProjectNameError,
    ProjectNotFoundError,
)
from lexigram.builder.graph.models import (
    GraphDocument,
    ValidatedGraph,
)
from lexigram.builder.graph.palette import is_snake_case_identifier
from lexigram.builder.graph.parsing import document_to_dict, parse_document
from lexigram.builder.graph.validation import validate
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

_logger = get_logger(__name__)

GRAPH_FILE = "graph.json"


class ProjectService:
    """CRUD over ``<projects_dir>/<name>/graph.json`` with atomic saves."""

    def __init__(self, projects_dir: Path) -> None:
        self.projects_dir = projects_dir

    def project_dir(self, name: str) -> Path:
        """Directory for one project."""
        return self.projects_dir / name

    def graph_path(self, name: str) -> Path:
        """Path of the stored graph document."""
        return self.project_dir(name) / GRAPH_FILE

    def list_projects(self) -> list[str]:
        """Sorted names of every project holding a graph document."""
        if not self.projects_dir.is_dir():
            return []
        return sorted(p.parent.name for p in self.projects_dir.glob(f"*/{GRAPH_FILE}"))

    def create(self, name: str) -> Result[Path, InvalidProjectNameError]:
        """Create an empty project with a fresh graph document."""
        if not is_snake_case_identifier(name):
            return Err(
                InvalidProjectNameError(f"project name {name!r} must be snake_case")
            )
        target = self.project_dir(name)
        if target.exists():
            return Err(InvalidProjectNameError(f"project {name!r} already exists"))
        target.mkdir(parents=True, exist_ok=False)
        empty = GraphDocument(version=1, nodes=(), edges=())
        self._write_graph_atomic(name, document_to_dict(empty))
        _logger.info("project_created", project=name)
        return Ok(target)

    def load_graph(self, name: str) -> Result[GraphDocument, BuilderError]:
        """Load and type-check the stored graph document."""
        path = self.graph_path(name)
        if not path.is_file():
            return Err(ProjectNotFoundError(f"unknown project {name!r}"))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return Err(GraphValidationError(f"unreadable graph: {exc}"))
        parsed = parse_document(data)
        if parsed.is_err():
            failure: BuilderError = parsed.unwrap_err()
            return Err(failure)
        return Ok(parsed.unwrap())

    def load_validated(self, name: str) -> Result[ValidatedGraph, BuilderError]:
        """Load then validate; both failures surface as Err."""
        loaded = self.load_graph(name)
        if loaded.is_err():
            failure: BuilderError = loaded.unwrap_err()
            return Err(failure)
        validated = validate(loaded.unwrap())
        if validated.is_err():
            vfailure: BuilderError = validated.unwrap_err()
            return Err(vfailure)
        return Ok(validated.unwrap())

    def save_graph(
        self, name: str, document: GraphDocument
    ) -> Result[None, BuilderError]:
        """Validate then atomically persist a graph document."""
        check = validate(document)
        if check.is_err():
            err = check.unwrap_err()
            return Err(
                GraphValidationError(
                    err.args[0] if err.args else "validation failed",
                    diagnostics=err.diagnostics,
                )
            )
        self._write_graph_atomic(name, document_to_dict(document))
        _logger.info("graph_saved", project=name)
        return Ok(None)

    def delete(self, name: str) -> Result[None, ProjectNotFoundError]:
        """Remove the whole project directory."""
        target = self.project_dir(name)
        if not target.is_dir():
            return Err(ProjectNotFoundError(f"unknown project {name!r}"))
        for child in sorted(target.rglob("*"), reverse=True):
            child.rmdir() if child.is_dir() else child.unlink()
        target.rmdir()
        _logger.info("project_deleted", project=name)
        return Ok(None)

    def _write_graph_atomic(self, name: str, payload: dict) -> None:
        target = self.graph_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        Path.replace(tmp, target)


__all__ = ["ProjectService"]
