"""Document repository generator for creating NoSQL repositories."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, cast

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class DocumentRepositoryGenerator(GeneratorBase):
    """Generator for creating document (NoSQL) repositories.

    Generates a repository class that extends ``DocumentRepository`` from
    ``lexigram-nosql``, with entity-to-document and document-to-entity
    conversion methods pre-scaffolded.
    """

    name = "document-repository"
    description = "Generate a NoSQL document repository"
    default_output_dir = "src/repositories"

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert snake_case or kebab-case to PascalCase."""
        return "".join(word.capitalize() for word in re.split(r"[-_]", name))

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert PascalCase or kebab-case to snake_case."""
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        s2 = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s1)
        return s2.replace("-", "_").lower()

    def generate(
        self,
        name: str,
        output_dir: str = "src/repositories",
        fields_str: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        """Generate a document repository.

        Args:
            name: Entity name (e.g. ``"user"``, ``"order"``).
            output_dir: Target directory for the generated file.
            fields_str: Optional comma-separated field definitions.
            **options: Extra options (``force`` to overwrite).

        Returns:
            GenerationResult with created file paths.
        """
        fields = []
        if fields_str:
            fields = parse_fields(fields_str)
        else:
            fields = [
                cast("FieldSpec", {"name": "id", "type": "str", "required": True}),
            ]

        output_path = Path(output_dir)
        entity_name = self._to_pascal_case(name)
        repo_filename = f"{self._to_snake_case(name)}_repository.py"
        collection_name = self._to_snake_case(name) + "s"

        context = {
            "entity_name": entity_name,
            "entity_name_snake": self._to_snake_case(name),
            "collection_name": collection_name,
            "fields": fields,
        }

        content = self.render_template("document_repository.py.jinja2", context)

        file_path = output_path / repo_filename
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()

        output_path.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)

        return GenerationResult(files_created=[output_path])
