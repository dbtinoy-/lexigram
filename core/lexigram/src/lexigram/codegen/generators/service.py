"""Shared service generator."""

from __future__ import annotations

from lexigram.codegen.base import GeneratorBase
from lexigram.contracts.cli.generators import GenerationResult


class ServiceGenerator(GeneratorBase):
    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: object,
    ) -> GenerationResult:
        name = self._strip_type_suffix(name, "Service")
        class_name = self._to_pascal_case(name)
        model_name = self._to_snake_case(name)
        file_path = self.output_dir / f"{model_name}_service.py"
        content = self.render_template(
            "service.py.jinja2",
            {
                "class_name": class_name,
                "model_name": model_name,
                "resource_name": self._pluralize(model_name),
            },
        )
        return self.write_file(file_path, content, dry_run=dry_run, force=force)

    @staticmethod
    def _strip_type_suffix(name: str, suffix: str) -> str:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
        return name

    def _pluralize(self, value: str) -> str:
        if value.endswith("y") and value[-2:-1] not in {"a", "e", "i", "o", "u"}:
            return f"{value[:-1]}ies"
        if value.endswith("s"):
            return value
        return f"{value}s"
