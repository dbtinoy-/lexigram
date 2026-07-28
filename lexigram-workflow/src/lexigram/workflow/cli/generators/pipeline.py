"""Pipeline generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class PipelineGenerator(TemplateGeneratorBase):
    """Generator for pipeline definitions."""

    name = "pipeline"
    description = "Generate a pipeline with sequential processing stages"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate pipeline files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("PipelineGenerator not yet implemented")
