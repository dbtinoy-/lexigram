"""Auth policy generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class AuthPolicyGenerator(TemplateGeneratorBase):
    """Generator for authorization policies."""

    name = "auth_policy"
    description = "Generate an authorization policy"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate auth policy files.

        Args:
            context: Template rendering context.

        Returns:
            List of generated file paths.
        """
        raise NotImplementedError("AuthPolicyGenerator not yet implemented")
