"""Exception filter generator for SQL CLI contributions."""

from __future__ import annotations

from typing import Any

from lexigram.sql.cli.generators.base import GenerationResult, GeneratorBase


class FilterGenerator(GeneratorBase):
    """Generator for exception filters."""

    name = "filter"
    description = "Generate an exception filter for error handling"
    default_output_dir = "src/filters"

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def generate(
        self,
        name: str,
        exception_type: str = "Exception",
        **kwargs: Any,
    ) -> GenerationResult:
        file_path = self.output_dir / f"{self._to_snake_case(name)}.py"
        result = GenerationResult()
        dry_run = bool(kwargs.get("dry_run", False))
        force = bool(kwargs.get("force", False))

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        rendered = self.env.get_template("filter.py.jinja2").render(
            name=name,
            exception_type=exception_type,
            snake_name=self._to_snake_case(name),
            snake_name_plural=f"{self._to_snake_case(name)}s",
        )

        if dry_run:
            result.files_created.append(file_path)
            return result

        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(rendered, encoding="utf-8")
        result.files_created.append(file_path)
        return result


__all__ = ["FilterGenerator"]
