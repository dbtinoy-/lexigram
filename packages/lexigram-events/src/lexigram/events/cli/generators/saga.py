"""Saga generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class SagaGenerator(TemplateGeneratorBase):
    """Generator for saga orchestrators."""

    name = "saga"
    description = "Generate a saga orchestrator with compensating actions"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate saga files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("SagaGenerator not yet implemented")
