"""Chained alembic migration generator for generated entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.contracts.cli.generators import GenerationResult, resolve_options
from lexigram.contracts.cli.parsers import parse_fields
from lexigram.sql.cli.generators.base import GeneratorBase


class EntityMigrationGenerator(GeneratorBase):
    """Generate an alembic revision creating the entity's table."""

    name = "migration"
    description = "Generate a chained alembic migration for an entity"

    _SA_TYPES = {
        "str": "String(length=255)", "string": "String(length=255)",
        "text": "Text",
        "int": "Integer", "integer": "Integer",
        "float": "Float",
        "bool": "Boolean", "boolean": "Boolean",
        "datetime": "DateTime(timezone=True)",
        "uuid": "String(length=32)",
    }

    def generate(
        self,
        name: str,
        fields_str: str | None = None,
        *,
        rev_id: str = "001",
        prev_rev: str | None = None,
        table_name: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        output_dir = options.pop("output_dir", None)
        if output_dir is not None:
            self.output_dir = Path(str(output_dir)).resolve()
        parsed = parse_fields(fields_str) if fields_str else []
        table = table_name or f"{self._to_snake_case(name)}s"

        column_lines = [
            f'        sa.Column("{f.name}",'
            f" sa.{self._SA_TYPES.get(f.type, 'String(length=255)')},"
            f" nullable={'False' if f.required else 'True'}"
            for f in parsed
        ]

        content = self.render_template(
            "entity_migration.py.jinja2",
            {
                "rev_id": rev_id,
                "prev_rev": prev_rev,
                "table": table,
                "column_lines": column_lines,
            },
        )

        file_path = (
            self.output_dir / f"{rev_id}_create_{table}.py"
        )
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(**options)))
