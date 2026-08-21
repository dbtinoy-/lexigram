"""Shared primitives for filesystem-backed code generators."""

from __future__ import annotations

import inspect
from pathlib import Path
import re
from typing import Any

import jinja2

from lexigram.contracts.cli.generators import GenerationResult as GenerationResult


class GeneratorBase:
    """Base for interactive code scaffolders (name-based, file-producing)."""

    def __init__(
        self,
        output_dir: str | Path = "src",
        template_root: str | Path | None = None,
    ) -> None:
        self.raw_output_dir = Path(output_dir)
        self.output_dir = self._resolve_output_dir(self.raw_output_dir)
        self.template_root = self._resolve_template_root(template_root)
        self._environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_root),
            autoescape=False,  # noqa: S701 - code generation templates are not HTML
            trim_blocks=False,
            lstrip_blocks=False,
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined,
        )

    def generate(self, name: str, **options: Any) -> GenerationResult:
        raise NotImplementedError

    @property
    def env(self) -> jinja2.Environment:
        """Public accessor for the Jinja2 environment."""
        return self._environment

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        template = self._environment.get_template(template_name)
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

        if existed and not force:
            return GenerationResult(files_skipped=[file_path])

        if not dry_run:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        if existed and force:
            return GenerationResult(files_overwritten=[file_path])

        return GenerationResult(files_created=[file_path])

    @staticmethod
    def _find_project_anchor(start: Path) -> Path | None:
        """Return the nearest ancestor directory with a real ``[project]`` table.

        Virtual workspace roots (``[tool.uv.workspace]`` only, no
        ``[project]``) are deliberately skipped: generated application code
        must never land in the framework monorepo.
        """

        for candidate in (start, *start.parents):
            pyproject = candidate / "pyproject.toml"
            if not pyproject.is_file():
                continue
            try:
                manifest = pyproject.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "[project]" in manifest:
                return candidate
        return None

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

        anchor = cls._find_project_anchor(Path.cwd())
        if anchor is None:
            raise ValueError(
                f"relative output_dir {output_dir.as_posix!r} cannot be "
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
        normalized = GeneratorBase._to_snake_case(name)
        return "".join(part.capitalize() for part in normalized.split("_") if part)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        compact = re.sub(r"[\s-]+", "_", name)
        separated = re.sub(r"([A-Z])", r"_\1", compact)
        return separated.lower().strip("_")

    @staticmethod
    def _get_package_name(output_dir: str | Path) -> str:
        """Convert an output directory path to a dotted Python package name."""
        return Path(output_dir).as_posix().replace("/", ".")


class TemplateGeneratorBase:
    """Base for programmatic template renderers (context-based, object-returning)."""

    def generate(self, context: dict[str, object]) -> list[object]:
        raise NotImplementedError
