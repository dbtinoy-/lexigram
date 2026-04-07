"""Health check generator for SQL CLI contributions."""

from __future__ import annotations

from typing import Any

from lexigram.sql.cli.generators.base import GenerationResult, GeneratorBase


class HealthCheckGenerator(GeneratorBase):
    """Generator for health checks."""

    name = "health"
    description = "Generate a health check for monitoring"
    default_output_dir = "src/health"

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def generate(
        self,
        name: str,
        critical: bool = True,
        **kwargs: Any,
    ) -> GenerationResult:
        file_path = self.output_dir / f"{self._to_snake_case(name)}.py"
        result = GenerationResult()
        dry_run = bool(kwargs.get("dry_run", False))
        force = bool(kwargs.get("force", False))

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        rendered = self.env.get_template("health_check.py.jinja2").render(
            name=name,
            snake_name=self._to_snake_case(name),
            critical=critical,
        )

        if dry_run:
            result.files_created.append(file_path)
            return result

        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(rendered, encoding="utf-8")
        result.files_created.append(file_path)
        return result


__all__ = ["HealthCheckGenerator"]
