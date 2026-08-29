"""Search index generator for creating searchable models and indexes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import FieldSpec, GenerationResult, GeneratorBase, parse_fields
from lexigram.contracts.cli.generators import resolve_options


class SearchIndexGenerator(GeneratorBase):
    """Generate a search index with indexing and querying."""

    name = "search_index"
    description = "Generate a search index with indexing and querying"
    default_output_dir = "src/search"

    def __init__(self, output_dir: str | Path = "src/search") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        fields_str: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a search index module.

        Args:
            name: Index name (e.g. ``"Product"`` or ``"product"``).
            fields_str: Optional ``name:type`` field list in parser syntax.
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        fields = (
            parse_fields(fields_str)
            if fields_str
            else [
                FieldSpec(name="id", type="str", required=True),
                FieldSpec(name="title", type="str", required=True),
                FieldSpec(name="content", type="str", required=False),
                FieldSpec(name="created_at", type="datetime", required=False),
            ]
        )
        backend = str(options.get("backend", "meilisearch"))
        index_name = self._to_pascal_case(name)
        index_snake = self._to_snake_case(name)
        context: dict[str, Any] = {
            "index_name": index_name,
            "index_name_snake": index_snake,
            "fields": fields,
            "backend": backend,
        }
        content = self.render_template("search_index.py.jinja2", context)
        file_path = self.output_dir / f"{index_snake}_index.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["SearchIndexGenerator"]
