"""Vector collection generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class VectorCollectionGenerator(GeneratorBase):
    """Generate a vector collection definition."""

    name = "vector_collection"
    description = "Generate a vector collection definition with backend registration"
    default_output_dir = "src/collections"

    def __init__(self, output_dir: str | Path = "src/collections") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a vector collection definition module.

        Args:
            name: Collection name (e.g. ``"ProductEmbeddings"`` or ``"product_embeddings"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        collection_name = self._to_pascal_case(name)
        collection_snake = self._to_snake_case(name)
        context: dict[str, Any] = {
            "collection_name": collection_name,
            "collection_name_snake": collection_snake,
        }
        content = self.render_template("vector_collection.py.jinja2", context)
        file_path = self.output_dir / f"{collection_snake}_collection.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["VectorCollectionGenerator"]
