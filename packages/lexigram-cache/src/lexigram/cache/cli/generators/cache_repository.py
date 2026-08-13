"""Cache repository generator for creating cached data repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import FieldSpec, GenerationResult, GeneratorBase, parse_fields

_DEFAULT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(name="id", type="int", required=True),
    FieldSpec(name="name", type="str", required=True),
)


class CacheRepositoryGenerator(GeneratorBase):
    """Generator for creating cached repositories."""

    name = "cache_repo"
    description = "Generate a cached repository with cache-aside pattern"
    default_output_dir = "src/repositories"
    template_name = "cache_repository.py.jinja2"

    def __init__(self, output_dir: str | Path = "src/repositories") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        output_dir: str | Path | None = None,
        fields_str: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a cached repository."""
        fields: list[FieldSpec] = (
            parse_fields(fields_str) if fields_str else list(_DEFAULT_FIELDS)
        )

        output_path = Path(output_dir) if output_dir is not None else self.output_dir
        entity_name = self._to_pascal_case(name)
        repo_snake = self._to_snake_case(name)
        file_path = output_path / f"{repo_snake}_repository.py"

        pk_name, pk_type = self._derive_pk(fields)
        # Avoid shadowing the Python builtin 'id' in generated method signatures.
        pk_param = f"entity_{pk_name}" if pk_name == "id" else pk_name

        content = self.render_template(
            self.template_name,
            {
                "entity_name": entity_name,
                "repo_name_snake": repo_snake,
                "fields": fields,
                "pk_name": pk_name,
                "pk_type": pk_type,
                "pk_param": pk_param,
            },
        )

        return self.write_file(file_path, content, dry_run=dry_run, force=force)

    @staticmethod
    def _derive_pk(fields: list[FieldSpec]) -> tuple[str, str]:
        """Derive the primary-key name and type from the field list.

        Prefers a field named ``id``.  Falls back to the first field.
        Returns ``("id", "int")`` when the field list is empty.
        """
        for f in fields:
            if f.name == "id":
                return f.name, f.type
        if fields:
            first = fields[0]
            return first.name, first.type
        return "id", "int"


__all__ = ["CacheRepositoryGenerator"]
