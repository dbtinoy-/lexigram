"""Seeder generator for database seed data."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.cli.parsers import parse_fields
from lexigram.sql.cli.generators.base import GenerationResult, GeneratorBase


class SeederGenerator(GeneratorBase):
    """Generates a database seeder file."""

    name = "seeder"
    description = "Generate a database seeder file"
    default_output_dir = "seeds"

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def generate(
        self,
        name: str,
        **kwargs: Any,
    ) -> GenerationResult:
        result = GenerationResult()
        dry_run = bool(kwargs.get("dry_run", False))
        force = bool(kwargs.get("force", False))

        fields_raw = kwargs.get("fields") or kwargs.get("fields_str") or ""
        field_specs = parse_fields(fields_raw) if isinstance(fields_raw, str) else []
        fields = [
            {
                "name": spec.name,
                "type": spec.type,
                "required": spec.required,
                "unique": spec.unique,
                "fk": spec.fk,
                "default": spec.default,
                "sample_value": self._get_sample_value(name, spec.name, spec.type),
            }
            for spec in field_specs
        ]

        table_name = self._to_snake_case(name)
        file_path = self.output_dir / f"{table_name}.py"

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        if dry_run:
            result.files_created.append(file_path)
            return result

        content = self.env.get_template("seeder.py.jinja2").render(
            model_name=self._to_pascal_case(name),
            file_name=table_name,
            table_name=table_name,
            fields=fields,
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        result.files_created.append(file_path)
        return result

    def _get_sample_value(
        self, model_name: str, field_name: str, field_type: str
    ) -> str:
        lowered_type = field_type.lower()
        lowered_name = field_name.lower()
        lowered_model = model_name.lower()

        if "email" in lowered_name:
            return f'"{lowered_model}@example.com"'
        if "name" in lowered_name and "user" in lowered_name:
            return f'"John {self._to_pascal_case(model_name)}"'
        if "name" in lowered_name:
            return f'"Sample {self._to_pascal_case(model_name)}"'
        if "title" in lowered_name:
            return f'"Sample {self._to_pascal_case(model_name)} Title"'
        if "description" in lowered_name:
            return f'"This is a sample description for {lowered_model}"'
        if "url" in lowered_name or "link" in lowered_name:
            return f'"https://example.com/{lowered_model}"'
        if "phone" in lowered_name:
            return '"+1234567890"'
        if "address" in lowered_name:
            return '"123 Main St, City, Country"'
        if (
            "price" in lowered_name
            or "amount" in lowered_name
            or "cost" in lowered_name
        ):
            return "99.99"
        if "count" in lowered_name or "quantity" in lowered_name:
            return "1"
        if "age" in lowered_name:
            return "25"
        if lowered_name.startswith(("is_", "has_")) or "active" in lowered_name:
            return "True"
        if lowered_type in {"int", "integer"}:
            return "1"
        if lowered_type in {"float", "double", "decimal"}:
            return "1.0"
        if lowered_type in {"bool", "boolean"}:
            return "True"
        if lowered_type in {"date", "datetime"}:
            return "datetime.now(timezone.utc)"
        if lowered_type == "uuid":
            return '"550e8400-e29b-41d4-a716-446655440000"'
        if "json" in lowered_type:
            return '{"key": "value"}'
        return f'"sample_{lowered_name}"'


__all__ = ["SeederGenerator"]
