"""Metric generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class MetricGenerator(TemplateGeneratorBase):
    """Generator for custom metric definitions."""

    name = "metric"
    description = "Generate a custom metric definition with backend registration"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate metric definition files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("MetricGenerator not yet implemented")
