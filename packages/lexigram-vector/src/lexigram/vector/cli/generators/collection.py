"""Vector collection generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class VectorCollectionGenerator(TemplateGeneratorBase):
    """Generator for vector collection definitions."""

    name = "vector_collection"
    description = "Generate a vector collection definition with backend registration"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate vector collection files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("VectorCollectionGenerator not yet implemented")
