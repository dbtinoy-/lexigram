"""Saga step generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class SagaStepGenerator(TemplateGeneratorBase):
    """Generator for saga steps with compensating transactions."""

    name = "saga_step"
    description = "Generate a saga step with compensating transaction"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate saga step files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("SagaStepGenerator not yet implemented")
