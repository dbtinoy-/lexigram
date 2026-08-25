"""Shared primitives for filesystem-backed code generators."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lexigram.contracts.cli.generators import (
    CollisionPolicy as CollisionPolicy,
)
from lexigram.contracts.cli.generators import (
    GenerationOptions as GenerationOptions,
)
from lexigram.contracts.cli.generators import (
    GenerationResult as GenerationResult,
)
from lexigram.contracts.cli.generators import (
    find_project_anchor as find_project_anchor,
)
from lexigram.contracts.cli.generators import (
    pascal_case as pascal_case,
)
from lexigram.contracts.cli.generators import (
    resolve_options as resolve_options,
)
from lexigram.contracts.cli.generators import (
    snake_case as snake_case,
)
from lexigram.contracts.cli.generators import (
    validate_component_name as validate_component_name,
)
from lexigram.contracts.exceptions.infra import CollidingFileError, InfrastructureError

if TYPE_CHECKING:
    import jinja2


class GeneratorBase:
    """Base for interactive code scaffolders (name-based, file-producing).

    Rendering requires the optional ``codegen`` extra
    (``uv add 'lexigram[codegen]'``); construction, name normalization,
    and guarded file writes work without it.
    """

    def __init__(
        self,
        output_dir: str | Path = "src",
        template_root: str | Path | None = None,
    ) -> None:
        self.raw_output_dir = Path(output_dir)
        self.output_dir = self._resolve_output_dir(self.raw_output_dir)
        self.template_root = self._resolve_template_root(template_root)
        self._environment: jinja2.Environment | None = None
        self._staged: list[tuple[Path, str]] = []

    def generate(self, name: str, **options: Any) -> GenerationResult:
        raise NotImplementedError

    # ── staged generation ────────────────────────────────────────────

    def stage(self, rel_path: str | Path, content: str) -> None:
        """Queue a rendered file for the next :meth:`commit`.

        Validates immediately (traversal guard, duplicate detection) so a
        misdirected or double-staged file fails before any I/O.

        Args:
            rel_path: Path relative to ``output_dir`` (absolute paths are
                accepted when already inside ``output_dir``).
            content: Full rendered file content.

        Raises:
            ValueError: If the path escapes ``output_dir`` or was already
                staged in this run.
        """
        target = self._ensure_inside_output(rel_path)
        for staged_path, _ in self._staged:
            if staged_path == target:
                raise ValueError(f"Path {target} is already staged")
        self._staged.append((target, content))

    def commit(self, options: GenerationOptions | None = None) -> GenerationResult:
        """Validate and write every staged file atomically (validate-all-then-write-all).

        Collision checks against disk run for **all** staged paths before
        the first byte is written; under
        :attr:`CollisionPolicy.FAIL` any collision raises
        ``CollidingFileError`` leaving the tree untouched. Writes happen
        in sorted path order for deterministic trees.

        Args:
            options: Fully-resolved run options; defaults to SKIP.

        Returns:
            The resulting :class:`GenerationResult`. With ``dry_run`` the
            same result is computed without touching disk.

        Raises:
            CollidingFileError: Under the FAIL policy when a staged path
                already exists.
        """
        resolved = options if options is not None else resolve_options()
        actions: dict[Path, str] = {}
        for target, _content in self._staged:
            if not target.exists():
                actions[target] = "created"
            elif resolved.policy is CollisionPolicy.OVERWRITE:
                actions[target] = "overwritten"
            elif resolved.policy is CollisionPolicy.FAIL:
                raise CollidingFileError(
                    f"Generated file {target} collides with an existing "
                    "file under collision policy FAIL"
                )
            else:
                actions[target] = "skipped"

        created: list[Path] = []
        skipped: list[Path] = []
        overwritten: list[Path] = []
        for target in sorted(actions, key=str):
            action = actions[target]
            if action == "skipped":
                skipped.append(target)
                continue
            content = next(c for p, c in self._staged if p == target)
            if not resolved.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            if action == "overwritten":
                overwritten.append(target)
            else:
                created.append(target)

        self._staged = []
        return GenerationResult(
            files_created=created,
            files_skipped=skipped,
            files_overwritten=overwritten,
        )

    def finalize(self, result: GenerationResult) -> GenerationResult:
        """Post-commit hook for transforms (formatting, verification).

        Subclasses override to post-process committed files; the default
        returns *result* unchanged.
        """
        return result

    @property
    def env(self) -> jinja2.Environment:
        """Public accessor for the Jinja2 environment (lazy-built)."""
        if self._environment is None:
            self._environment = self._build_environment()
        return self._environment

    def _build_environment(self) -> jinja2.Environment:
        try:
            import jinja2
        except ImportError as exc:
            raise InfrastructureError(
                "jinja2 is required for template rendering but is not "
                "installed. Install the codegen extra: "
                "uv add 'lexigram[codegen]' (or pip install 'lexigram[codegen]')"
            ) from exc
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_root),
            autoescape=False,  # noqa: S701 - code generation templates are not HTML
            trim_blocks=False,
            lstrip_blocks=False,
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined,
        )

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)

    def write_file(
        self,
        file_path: Path,
        content: str,
        *,
        dry_run: bool = False,
        force: bool = False,
    ) -> GenerationResult:
        existed = file_path.exists()

        self._ensure_inside_output(file_path)

        if existed and not force:
            return GenerationResult(files_skipped=[file_path])

        if not dry_run:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        if existed and force:
            return GenerationResult(files_overwritten=[file_path])

        return GenerationResult(files_created=[file_path])

    def _ensure_inside_output(self, rel_path: str | Path) -> Path:
        """Resolve *rel_path* against ``output_dir`` and enforce the traversal guard.

        Returns:
            The resolved absolute target path.

        Raises:
            ValueError: If the resolved path escapes ``output_dir``.
        """
        target = Path(rel_path)
        if not target.is_absolute():
            target = Path(self.output_dir) / target

        # Path-traversal guard: the resolved target must stay inside the
        # generator's output directory (spec finding 15).
        base = Path(self.output_dir).resolve()
        resolved = target.resolve()
        if not resolved.is_relative_to(base):
            raise ValueError(
                f"Generated path {rel_path} escapes output directory {base}"
            )
        return target

    @classmethod
    def _resolve_output_dir(cls, output_dir: Path) -> Path:
        """Resolve ``output_dir`` to an absolute path before any fs mutation.

        Absolute paths pass through untouched. Relative paths anchor to the
        nearest ancestor with a real project manifest, so generators invoked
        from a subdirectory still write into the right package. Refusal
        happens here — before any ``mkdir`` — so a misdirected run leaves no
        stray directories behind.

        Raises:
            ValueError: If a relative path has no resolvable project anchor.
        """

        if output_dir.is_absolute():
            return output_dir

        anchor = find_project_anchor(Path.cwd())
        if anchor is None:
            raise ValueError(
                f"relative output_dir {output_dir.as_posix()!r} cannot be "
                "resolved: run inside the package that should receive the "
                "generated code, or pass an absolute --output-dir"
            )
        return anchor / output_dir

    def _resolve_template_root(self, template_root: str | Path | None) -> Path:
        if template_root is not None:
            return Path(template_root)

        module_path = Path(inspect.getfile(self.__class__)).resolve().parent
        candidates = [module_path / "templates", module_path.parent / "templates"]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[-1]

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        return pascal_case(name)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        return snake_case(name)

    @classmethod
    def _validate_component_name(cls, name: str) -> str:
        return validate_component_name(name)

    @staticmethod
    def _get_package_name(output_dir: str | Path) -> str:
        """Convert an output directory path to a dotted Python package name."""
        return Path(output_dir).as_posix().replace("/", ".")


class TemplateGeneratorBase:
    """Base for programmatic template renderers (context-based, object-returning)."""

    def generate(self, context: dict[str, object]) -> list[object]:
        raise NotImplementedError
