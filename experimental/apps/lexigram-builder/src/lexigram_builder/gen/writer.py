"""Project writer — orchestrates code generation from a parsed graph document.

``ProjectWriter.write_project`` collects node configs, invokes framework
generators, emits scaffold files, and prunes stale generated files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lexigram_builder.gen.emitters.scaffold import emit_scaffold_files
from lexigram_builder.gen.node_generators import (
    ENTITY_ATTACHED,
    VERB_SPECS,
    entity_attached_extra_kwargs,
    get_verb_spec,
)
from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    EntityConfig,
    FeatureFlagConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
)
from lexigram_builder.graph.palette import (
    KIND_AUTH,
    KIND_CONTRACT,
    KIND_ENTITY,
    KIND_FEATURE_FLAG,
    KIND_RATE_LIMIT,
    KIND_ROLE,
    KIND_ROUTE,
)


@dataclass
class GenerationReport:
    """Report of a generation run.

    Attributes:
        files_created: Paths of files created.
        files_overwritten: Paths of files overwritten.
        files_skipped: Paths of files skipped (already exist).
        errors: Error messages encountered.
    """

    files_created: list[str] = field(default_factory=list)
    files_overwritten: list[str] = field(default_factory=list)
    files_skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return ``True`` if no errors occurred."""
        return not self.errors


# ── Stale-file pruning ────────────────────────────────────────────────

# Directories that receive generated code.  Any file inside these that
# was not written during the current run is pruned.
_GENERATED_DIRS: frozenset[str] = frozenset(
    {
        "src/app/features",
        "src/app/guards",
        "src/app/contracts",
        "src/app/models",
        "src/app/services",
        "src/app/jobs",
        "src/app/controllers",
    }
)


def _prune_stale_generated(
    project_dir: Path,
    written_paths: set[Path],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Remove files in generated dirs that were not written this run.

    Args:
        project_dir: Root of the generated project.
        written_paths: Absolute paths written during this run.
        dry_run: If ``True``, report but don't delete.

    Returns:
        List of pruned file paths (as strings).
    """
    pruned: list[str] = []
    for dir_rel in _GENERATED_DIRS:
        dir_path = project_dir / dir_rel
        if not dir_path.exists():
            continue
        for file_path in dir_path.rglob("*.py"):
            if file_path.resolve() not in written_paths:
                pruned.append(str(file_path))
                if not dry_run:
                    file_path.unlink()
    return pruned


# ── Generator loading ─────────────────────────────────────────────────


def _load_generator(
    generator_name: str,
    output_dir: str,
    *,
    package: str = "",
) -> Any:
    """Load a framework generator by name.

    This is a simplified loader that imports the generator class from the
    known framework packages.  In a full implementation, this would use
    the CLI's ``GeneratorRegistry.get_adapter()``.

    Args:
        generator_name: The CLI generator name (e.g. ``"feature_flag"``).
        output_dir: Output directory for the generator.
        package: The framework package that owns the generator.

    Returns:
        A generator instance.

    Raises:
        ImportError: If the generator cannot be loaded.
    """
    # Map generator names to their import paths.
    _GENERATOR_PATHS: dict[str, str] = {
        "feature_flag": "lexigram.features.cli.generators.flag:FeatureFlagGenerator",
        "auth_guard": "lexigram.auth.cli.generators.auth_guard:AuthGuardGenerator",
        "guard": "lexigram.auth.cli.generators.guard:AuthGuardGenerator",
        "auth_policy": "lexigram.auth.cli.generators.auth_policy:AuthPolicyGenerator",
        "contract": "lexigram.web.cli.generators.interceptor:InterceptorGenerator",
        "model": "lexigram.web.cli.generators.controller:ControllerGenerator",
        "resource": "lexigram.web.cli.generators.resource:ResourceGenerator",
        "controller": "lexigram.web.cli.generators.controller:ControllerGenerator",
        "service": "lexigram.web.cli.generators.controller:ControllerGenerator",
        "job": "lexigram.web.cli.generators.controller:ControllerGenerator",
    }

    path = _GENERATOR_PATHS.get(generator_name)
    if path is None:
        raise ImportError(f"Unknown generator: {generator_name!r}")

    module_path, _, class_name = path.partition(":")
    from importlib import import_module

    module = import_module(module_path)
    cls = getattr(module, class_name)
    return cls(output_dir=output_dir)


# ── Project writer ────────────────────────────────────────────────────


class ProjectWriter:
    """Orchestrates code generation from a parsed graph document.

    Args:
        project_dir: Root directory of the generated project.
        dry_run: If ``True``, compute but don't write.
        force: If ``True``, overwrite existing files.
    """

    def __init__(
        self,
        project_dir: str | Path,
        *,
        dry_run: bool = False,
        force: bool = False,
    ) -> None:
        self.project_dir = Path(project_dir)
        self.dry_run = dry_run
        self.force = force
        self._written_paths: set[Path] = set()

    def write_project(self, doc: dict[str, Any]) -> GenerationReport:
        """Generate a full project from a parsed graph document.

        Args:
            doc: Parsed graph document (output of ``parse_document``).

        Returns:
            A :class:`GenerationReport` with the results.
        """
        report = GenerationReport()

        # ── Collect configs ───────────────────────────────────────────
        routes: list[RouteConfig] = []
        features: list[FeatureFlagConfig] = []
        auth_configs: list[AuthConfig] = []
        role_configs: list[RoleConfig] = []
        rate_limit_configs: list[RateLimitConfig] = []
        contract_configs: list[ContractConfig] = []
        entities: dict[str, EntityConfig] = {}

        # Build edge index: source_id → list of (target_id, edge_kind)
        edges_by_source: dict[str, list[tuple[str, str]]] = {}
        for edge in doc.get("edges", []):
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            kind = edge.get("kind", "")
            edges_by_source.setdefault(src, []).append((tgt, kind))

        # Index nodes by id
        node_map: dict[str, dict[str, Any]] = {
            n["id"]: n for n in doc.get("nodes", [])
        }

        for node in doc.get("nodes", []):
            kind = node["kind"]
            config = node["config"]

            if kind == KIND_ROUTE:
                routes.append(config)
            elif kind == KIND_FEATURE_FLAG:
                features.append(config)
            elif kind == KIND_AUTH:
                auth_configs.append(config)
            elif kind == KIND_ROLE:
                role_configs.append(config)
            elif kind == KIND_RATE_LIMIT:
                rate_limit_configs.append(config)
            elif kind == KIND_CONTRACT:
                contract_configs.append(config)
            elif kind == KIND_ENTITY:
                entities[node["id"]] = config

        # ── Emit generators ───────────────────────────────────────────
        gen_dirs: dict[str, str] = {
            spec.kind: spec.output_dir for spec in VERB_SPECS
        }

        for node in doc.get("nodes", []):
            kind = node["kind"]
            config = node["config"]
            spec = get_verb_spec(kind)

            if spec is None:
                continue

            # Resolve name from config
            name = getattr(config, "name", None)
            if name is None:
                continue

            output_dir = str(self.project_dir / spec.output_dir)

            try:
                generator = _load_generator(
                    spec.generator_name,
                    output_dir,
                    package=spec.package,
                )

                # Build generator kwargs
                gen_kwargs: dict[str, Any] = {}
                if self.force:
                    gen_kwargs["force"] = True

                # Entity-attached nodes get extra kwargs
                if kind in ENTITY_ATTACHED:
                    # Find the entity this node is wired to
                    for target_id, _edge_kind in edges_by_source.get(node["id"], []):
                        if target_id in entities:
                            entity = entities[target_id]
                            gen_kwargs.update(
                                entity_attached_extra_kwargs(
                                    kind, entity.name, entity.fields
                                )
                            )
                            break

                result = generator.generate(name, **gen_kwargs)

                if result.files_created:
                    report.files_created.extend(
                        str(p) for p in result.files_created
                    )
                    self._written_paths.update(
                        Path(p).resolve() for p in result.files_created
                    )
                if result.files_overwritten:
                    report.files_overwritten.extend(
                        str(p) for p in result.files_overwritten
                    )
                    self._written_paths.update(
                        Path(p).resolve() for p in result.files_overwritten
                    )
                if result.files_skipped:
                    report.files_skipped.extend(
                        str(p) for p in result.files_skipped
                    )

            except (ImportError, RuntimeError, OSError) as exc:
                report.errors.append(
                    f"Failed to generate {kind} {name!r}: {exc}"
                )

        # ── Emit scaffold files ───────────────────────────────────────
        try:
            scaffold = emit_scaffold_files(
                project_name=self.project_dir.name,
                routes=tuple(routes),
                features=tuple(features),
                auth_configs=tuple(auth_configs),
                role_configs=tuple(role_configs),
                rate_limit_configs=tuple(rate_limit_configs),
                contract_configs=tuple(contract_configs),
            )

            # Write main.py
            main_py_path = self.project_dir / "main.py"
            if not self.dry_run:
                main_py_path.parent.mkdir(parents=True, exist_ok=True)
                main_py_path.write_text(scaffold.main_py, encoding="utf-8")
            report.files_created.append(str(main_py_path))
            self._written_paths.add(main_py_path.resolve())

            # Write DI provider
            di_path = self.project_dir / "di_provider.py"
            if not self.dry_run:
                di_path.parent.mkdir(parents=True, exist_ok=True)
                di_path.write_text(scaffold.di_provider, encoding="utf-8")
            report.files_created.append(str(di_path))
            self._written_paths.add(di_path.resolve())

            # Write additional modules
            for module_name, module_content in scaffold.modules:
                module_path = self.project_dir / "src" / "app" / "guards" / module_name
                if not self.dry_run:
                    module_path.parent.mkdir(parents=True, exist_ok=True)
                    module_path.write_text(module_content, encoding="utf-8")
                report.files_created.append(str(module_path))
                self._written_paths.add(module_path.resolve())

        except (OSError, RuntimeError) as exc:
            report.errors.append(f"Failed to emit scaffold: {exc}")

        # ── Prune stale files ─────────────────────────────────────────
        try:
            pruned = _prune_stale_generated(
                self.project_dir,
                self._written_paths,
                dry_run=self.dry_run,
            )
            # Pruned files are informational, not errors.
            report.files_skipped.extend(pruned)
        except OSError as exc:
            report.errors.append(f"Failed to prune stale files: {exc}")

        return report


__all__ = ["GenerationReport", "ProjectWriter"]
