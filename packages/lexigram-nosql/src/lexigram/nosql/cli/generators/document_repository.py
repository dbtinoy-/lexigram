"""Document repository generator for creating NoSQL repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import FieldSpec, GenerationResult, GeneratorBase, parse_fields
from lexigram.contracts.cli.generators import resolve_options


class DocumentRepositoryGenerator(GeneratorBase):
    """Generate a NoSQL document repository.

    Generates a repository class extending the ``DocumentRepository``
    base from ``lexigram-nosql``, with entity-to-document and
    document-to-entity conversion methods pre-scaffolded.
    """

    name = "document_repo"
    description = "Generate a NoSQL document repository"
    default_output_dir = "src/repositories"

    def __init__(self, output_dir: str | Path = "src/repositories") -> None:
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
        """Generate a document repository.

        Args:
            name: Entity name (e.g. ``"user"``, ``"order"``).
            fields_str: Optional comma-separated field definitions.
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        fields = (
            parse_fields(fields_str)
            if fields_str
            else [FieldSpec(name="id", type="str", required=True)]
        )
        entity_name = self._to_pascal_case(name)
        entity_snake = self._to_snake_case(name)
        context: dict[str, Any] = {
            "entity_name": entity_name,
            "entity_name_snake": entity_snake,
            "collection_name": f"{entity_snake}s",
            "fields": fields,
        }
        content = self.render_template("document_repository.py.jinja2", context)
        file_path = self.output_dir / f"{entity_snake}_repository.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["DocumentRepositoryGenerator"]
