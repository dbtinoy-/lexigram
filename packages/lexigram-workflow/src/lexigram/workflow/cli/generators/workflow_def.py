"""Workflow definition generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class WorkflowDefinitionGenerator(TemplateGeneratorBase):
    """Generator for workflow definitions."""

    name = "workflow_def"
    description = "Generate a workflow definition with steps and transitions"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate workflow definition files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("WorkflowDefinitionGenerator not yet implemented")
