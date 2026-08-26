"""Pydantic entity-model generator (entity + Create/Update DTOs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.contracts.cli.generators import GenerationResult, resolve_options
from lexigram.contracts.cli.parsers import parse_fields
from lexigram.sql.cli.generators.base import GeneratorBase


class EntityModelGenerator(GeneratorBase):
    """Generate a Pydantic entity model with Create/Update DTOs."""

    name = "model"
    description = "Generate a Pydantic entity model with DTOs"

    _PY_TYPES = {
        "str": "str", "string": "str", "text": "str",
        "int": "int", "integer": "int",
        "float": "float", "bool": "bool", "boolean": "bool",
        "datetime": "datetime", "uuid": "str",
    }

    def generate(
        self,
        name: str,
        fields_str: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        output_dir = options.pop("output_dir", None)
        if output_dir is not None:
            self.output_dir = Path(str(output_dir)).resolve()
        parsed = parse_fields(fields_str) if fields_str else []
        py_types = self._PY_TYPES

        needs_datetime = any(
            py_types.get(f.type) == "datetime" for f in parsed
        )
        model_lines: list[str] = [
            "    id: str = Field(default_factory=lambda: str(uuid.uuid4()))",
        ]
        if needs_datetime:
            model_lines += [
                "    created_at: datetime = Field(",
                "        default_factory=lambda: datetime.now(timezone.utc)",
                "    )",
                "    updated_at: datetime = Field(",
                "        default_factory=lambda: datetime.now(timezone.utc)",
                "    )",
            ]
        create_lines: list[str] = []
        update_lines: list[str] = []

        for f in parsed:
            py = py_types.get(f.type, "str")
            opt = "" if f.required else " | None = None"
            if py == "datetime":
                model_lines.append(f"    {f.name}: datetime")
                create_lines.append(f"    {f.name}: str")
                update_lines.append(f"    {f.name}: str | None = None")
                continue
            model_lines.append(f"    {f.name}: {py}{opt}")
            create_lines.append(f"    {f.name}: {py}" + opt)
            update_lines.append(f"    {f.name}: {py} | None = None")

        content = self.render_template(
            "entity_model.py.jinja2",
            {
                "entity_name": self._to_pascal_case(name),
                "model_name": self._to_snake_case(name),
                "fields": [
                    {"name": f.name,
                     "py_type": py_types.get(f.type, "str"),
                     "required": f.required}
                    for f in parsed
                ],
                "needs_datetime": needs_datetime,
                "create_fields": create_lines or ["    pass"],
                "update_fields": update_lines or ["    pass"],
            },
        )

        file_path = self.output_dir / f"{self._to_snake_case(name)}.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(**options)))
