"""Tenant resolver generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class TenantResolverGenerator(GeneratorBase):
    """Generator for custom tenant resolver strategies."""

    name = "tenant_resolver"
    description = "Generate a custom tenant resolver strategy"
    default_output_dir = "src/tenancy"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a tenant resolver strategy module.

        Args:
            name: Resolver name (e.g. ``"HeaderTenant"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        resolver_name = self._to_pascal_case(name)
        resolver_snake = self._to_snake_case(name)
        context = {
            "resolver_name": resolver_name,
            "resolver_name_snake": resolver_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("tenant_resolver.py.jinja2", context)
        file_path = self.output_dir / f"{resolver_snake}_tenant_resolver.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
