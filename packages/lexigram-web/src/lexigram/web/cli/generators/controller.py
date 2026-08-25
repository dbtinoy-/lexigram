"""Controller generator."""

from __future__ import annotations

from pathlib import Path

from lexigram.codegen import GenerationResult, GeneratorBase, parse_fields
from lexigram.contracts.cli.generators import resolve_options


class ControllerGenerator(GeneratorBase):
    """Generate a controller class with CRUD endpoints."""

    def __init__(self, output_dir: str | Path = "src/controllers") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        fields_str: str | None = None,
        path: str | None = None,
        doc: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: object,
    ) -> GenerationResult:
        name = self._strip_type_suffix(name, "Controller")
        model_name = self._to_snake_case(name)
        resource_name = self._pluralize(model_name)
        api_path = path or f"/{resource_name}"
        fields = parse_fields(fields_str or "")
        file_path = self.output_dir / f"{model_name}_controller.py"
        content = self.render_template(
            "controller.py.jinja2",
            {
                "class_name": self._to_pascal_case(name),
                "model_name": model_name,
                "resource_name": resource_name,
                "resource_path": api_path.strip("/"),
                "doc": doc,
                "required_fields": [field.name for field in fields if field.required],
                "fields": [
                    {
                        "name": field.name,
                        "type": field.type,
                        "required": field.required,
                    }
                    for field in fields
                ],
            },
        )
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))

    @staticmethod
    def _strip_type_suffix(name: str, suffix: str) -> str:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
        return name

    @staticmethod
    def _pluralize(value: str) -> str:
        if value.endswith("y") and value[-2:-1] not in {"a", "e", "i", "o", "u"}:
            return f"{value[:-1]}ies"
        if value.endswith("s"):
            return value
        return f"{value}s"


__all__ = ["ControllerGenerator"]
