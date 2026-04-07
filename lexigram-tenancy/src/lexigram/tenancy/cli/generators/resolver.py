"""Tenant resolver generator."""

from __future__ import annotations

from lexigram.codegen.base import TemplateGeneratorBase


class TenantResolverGenerator(TemplateGeneratorBase):
    """Generator for custom tenant resolver strategies."""

    name = "tenant_resolver"
    description = "Generate a custom tenant resolver strategy"

    def generate(self, context: dict[str, object]) -> list[object]:
        """Generate tenant resolver files."""
        raise NotImplementedError("TenantResolverGenerator not yet implemented")
