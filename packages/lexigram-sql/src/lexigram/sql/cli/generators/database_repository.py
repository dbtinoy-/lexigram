"""Database repository generator for creating data repositories."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.cli.parsers import parse_fields
from lexigram.sql.cli.generators.base import GenerationResult, GeneratorBase


class DatabaseRepositoryGenerator(GeneratorBase):
    """Generator for creating database repositories."""

    name = "repository"
    description = "Generate a database repository"
    default_output_dir = "src/repositories"

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def generate(
        self,
        name: str,
        fields_str: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        parsed_fields = parse_fields(fields_str) if fields_str else []
        fields = [
            {
                "name": field.name,
                "type": field.type,
                "required": field.required,
            }
            for field in parsed_fields
        ]
        if not fields:
            fields = [{"name": "id", "type": "int", "required": True}]

        file_path = self.output_dir / f"{self._to_snake_case(name)}_repository.py"
        result = GenerationResult()
        dry_run = bool(options.get("dry_run", False))
        force = bool(options.get("force", False))

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        content = self.env.get_template("database_repository.py.jinja2").render(
            repo_name=self._to_pascal_case(name),
            repo_name_snake=self._to_snake_case(name),
            package_name=self._get_package_name(self.output_dir),
            fields=fields,
            entity_name=self._to_pascal_case(name),
        )

        if dry_run:
            result.files_created.append(file_path)
            return result

        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        result.files_created.append(file_path)
        return result


__all__ = ["DatabaseRepositoryGenerator"]
