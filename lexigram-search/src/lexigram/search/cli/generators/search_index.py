"""Search index generator for creating searchable models and indexes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.contracts.cli.generators import GenerationResult, GeneratorProtocol


class SearchIndexGenerator(GeneratorProtocol):
    """Generator for creating search indexes and searchable models."""

    name = "search_index"
    description = "Generate a search index with indexing and querying"
    default_output_dir = "src/search"

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert a name to PascalCase."""
        return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert a name to snake_case."""
        return name.replace("-", "_").lower()

    @staticmethod
    def _get_package_name(output_dir: str = "src/search") -> str:
        """Get package name from output directory path."""
        parts = Path(output_dir).parts
        if parts and parts[0] == "src":
            parts = parts[1:]
        return ".".join(parts) if parts else "app"

    def generate(
        self,
        name: str,
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a search index."""
        output_dir: str = kwargs.get("output_dir", "src/search")
        fields_str: str | None = kwargs.get("fields_str")

        # Parse fields if provided
        fields = []
        if fields_str:
            fields = parse_fields(fields_str)
        else:
            # Default fields for a basic searchable model
            fields = [
                FieldSpec(name="id", type="str", required=True),
                FieldSpec(name="title", type="str", required=True),
                FieldSpec(name="content", type="str", required=False),
                FieldSpec(name="created_at", type="datetime", required=False),
            ]

        # Determine backend
        options = kwargs
        backend = options.get("backend", "meilisearch")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Index class name
        index_name = self._to_pascal_case(name)
        index_filename = f"{self._to_snake_case(name)}_index.py"

        # Template context
        context = {
            "index_name": index_name,
            "index_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(output_dir),
            "fields": fields,
            "backend": backend,
            "_to_snake_case": self._to_snake_case,
            "_get_package_name": self._get_package_name,
        }

        # Render template
        env = Environment(
            loader=PackageLoader("lexigram.search.cli", "templates"),
            autoescape=select_autoescape(),
        )

        template = env.get_template("search_index.py.jinja2")
        content = template.render(**context)

        # Write file
        file_path = output_path / index_filename
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()

        with open(file_path, "w") as f:
            f.write(content)

        return GenerationResult(files_created=[output_path])
