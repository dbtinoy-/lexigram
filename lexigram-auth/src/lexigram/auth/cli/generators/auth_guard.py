"""Auth guard generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class AuthGuardGenerator(TemplateGeneratorBase):
    """Generator for authentication/authorization guards."""

    name = "auth_guard"
    description = "Generate an authentication/authorization guard"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate auth guard files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("AuthGuardGenerator not yet implemented")
