"""Vector collection generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class VectorCollectionGenerator(GeneratorBase):
    """Generator for vector collection definitions."""

    name = "vector_collection"
    description = "Generate a vector collection definition with backend registration"
    default_output_dir = "src/collections"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a vector collection definition module.

        Args:
            name: Collection name (e.g. ``"ProductEmbeddings"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        collection_name = self._to_pascal_case(name)
        collection_snake = self._to_snake_case(name)
        context = {
            "collection_name": collection_name,
            "collection_name_snake": collection_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("vector_collection.py.jinja2", context)
        file_path = self.output_dir / f"{collection_snake}_collection.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
