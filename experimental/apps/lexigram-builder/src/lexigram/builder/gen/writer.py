"""ProjectWriter — thin orchestrator over core codegen StagedGeneration."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from lexigram.builder.gen.emitters.controller_emitter import emit_controller_file
from lexigram.builder.gen.emitters.entity_emitter import emit_entity_files
from lexigram.builder.gen.emitters.scaffold import emit_scaffold_files
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    RouteConfig,
    ValidatedGraph,
)
from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import CollisionPolicy, GenerationOptions

__all__ = ["ProjectWriter"]

# Project dirs live at <pkg>/projects/<app>: five parent hops reach this
# monorepo checkout root, used for generated [tool.uv.sources] paths.
_REPO_ROOT_HOPS = 5


class ProjectWriter(GeneratorBase):
    """Writes a generated project tree for a validated graph.

    Stages every emitted file under ``<projects_root>/<app_name>`` and
    commits atomically with the OVERWRITE policy (regeneration wins —
    the canvas graph is the source of truth).

    Args:
        projects_root: Directory holding one subdirectory per project.
        post_process: When True, run ``ruff format`` over the committed
            project after a successful write (skipped when ruff absent).
    """

    def __init__(self, projects_root: Path, *, post_process: bool = False) -> None:
        super().__init__(output_dir=projects_root)
        self._post_process = post_process

    def write_project(self, graph: ValidatedGraph) -> GenerationResult:
        """Emit, stage, and commit the full project for *graph*."""
        settings_config = graph.settings().config
        assert isinstance(settings_config, AppSettingsConfig)
        app_name = settings_config.app_name

        entities: list[EntityConfig] = []
        for node in graph.entities():
            assert isinstance(node.config, EntityConfig)
            entities.append(node.config)
        by_id = {n.id: n for n in graph.document.nodes}
        ops_by_entity: dict[str, list[str]] = {}
        entity_by_name: dict[str, EntityConfig] = {}
        for route_node in graph.routes():
            dst_id = next(e.dst for e in graph.document.edges if e.src == route_node.id)
            dst_config = by_id[dst_id].config
            assert isinstance(route_node.config, RouteConfig)
            assert isinstance(dst_config, EntityConfig)
            bucket = ops_by_entity.setdefault(dst_config.name, [])
            bucket.extend(op for op in route_node.config.ops if op not in bucket)
            entity_by_name[dst_config.name] = dst_config

        files: dict[str, str] = {}
        files.update(
            emit_scaffold_files(
                app_name,
                entities,
                [(RouteConfig(ops=()), entity_by_name[name]) for name in ops_by_entity],
                relative_root=self._relative_monorepo_root(),
            )
        )
        assert all(isinstance(e, EntityConfig) for e in entities)
        for entity in entities:
            files.update(emit_entity_files(entity))
        for entity_name, ops in sorted(ops_by_entity.items()):
            rel_path, content = emit_controller_file(
                entity_by_name[entity_name], tuple(ops)
            )
            files[rel_path] = content

        app_prefix = f"{app_name}/"
        for rel_path in sorted(files):
            self.stage(app_prefix + rel_path, files[rel_path])

        result = self.commit(GenerationOptions(policy=CollisionPolicy.OVERWRITE))
        if self._post_process:
            self._ruff_format(Path(self.output_dir) / app_name)
        return self.finalize(result)

    def _relative_monorepo_root(self) -> str:
        """Relative path from a generated project dir back to this checkout root."""
        return "/".join([".."] * _REPO_ROOT_HOPS)

    def _ruff_format(self, project_dir: Path) -> None:
        ruff = shutil.which("ruff")
        if ruff is None:
            return
        subprocess.run(  # noqa: S603 - fixed argv, no shell
            [ruff, "format", "."],
            cwd=project_dir,
            check=False,
            capture_output=True,
            timeout=60,
        )
