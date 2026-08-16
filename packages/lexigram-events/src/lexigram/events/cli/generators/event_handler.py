"""Event handler generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class EventHandlerGenerator(TemplateGeneratorBase):
    """Generator for event handlers."""

    name = "event_handler"
    description = "Generate an event handler with bus registration"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate event handler files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("EventHandlerGenerator not yet implemented")
