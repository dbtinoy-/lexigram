"""ProjectWriter — thin orchestrator over core codegen StagedGeneration."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from lexigram.builder.gen.emitters.controller_emitter import emit_controller_file
from lexigram.builder.gen.emitters.entity_emitter import emit_entity_files
from lexigram.builder.graph.models import ValidatedGraph
from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import CollisionPolicy, GenerationOptions

__all__ = ["ProjectWriter"]


class ProjectWriter(GeneratorBase):
    """Writes a generated project tree for a validated graph.

    Stages every emitted file under ``<projects_root>/<app_name>`` and
    commits atomically with the OVERWRITE policy (regeneration wins —
    the canvas graph is the source of truth).
    """

    def __init__(
        self,
        projects_root: Path,
        *,
        post_process: bool = False,
    ) -> None:
        super().__init__(output_dir=projects_root)
        self._post_process = post_process

    def write_project(self, graph: ValidatedGraph) -> GenerationResult:
        """Emit, stage, and commit the full project for *graph*."""
        settings_config = graph.settings().config
        app_name: str = settings_config.app_name  # type: ignore[union-attr]

        files: dict[str, str] = {}
        entities: list = []
        bindings: list[tuple] = []
        by_id = {n.id: n for n in graph.document.nodes}
        for node in graph.entities():
            config = node.config
            assert isinstance(config, EntityConfig := type(config)) or True  # noqa: F841
            break
        for node in graph.entities():
            from lexigram.builder.graph.models import EntityConfig

            assert isinstance(node.config, EntityConfig)
            entities.append(node.config)
        for route_node in graph.routes():
            from lexigram.builder.graph.models import RouteConfig

            assert isinstance(route_node.config, RouteConfig)
            dst_id = next(
                e.dst
                for e in graph.document.edges
                if e.src == route_node.id
            )
            dst_node = by_id[dst_id]
            assert isinstance(dst_node.config, EntityConfig)
            bindings.append((route_node.config, dst_node.config))

        from lexigram.builder.gen.emitters.scaffold import emit_scaffold_files

        rel_root = self._relative_monorepo_root()
        files.update(
            emit_scaffold_files(
                app_name,
                entities,
                bindings,
                relative_root=rel_root,
            )
        )
        for entity in entities:
            files.update(emit_entity_files(entity))
        for route_cfg, entity_cfg in bindings:
            rel, content = emit_controller_file(route_cfg, entity_cfg)
            files[rel] = content

        app_prefix = f"{app_name}/"
        for rel_path in sorted(files):
            self.stage(app_prefix + rel_path, files[rel_path])

        result = self.commit(GenerationOptions(policy=CollisionPolicy.OVERWRITE))
        if self._post_process:
            self._ruff_format(Path(self.output_dir) / app_name)
        return self.finalize(result)

    def _relative_monorepo_root(self) -> str:
        """Relative path from a project dir back to this checkout root.

        Projects live at ``<pkg>/projects/<app>`` → five levels up.
        """
        return "../../..".replace("..", "..") + "/../.."

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
