"""Tenant resolver generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class TenantResolverGenerator(GeneratorBase):
    """Generate a custom tenant resolver strategy."""

    name = "tenant_resolver"
    description = "Generate a custom tenant resolver strategy"
    default_output_dir = "src/tenancy"

    def __init__(self, output_dir: str | Path = "src/tenancy") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a tenant resolver strategy module.

        Args:
            name: Resolver name (e.g. ``"HeaderTenant"`` or ``"header_tenant"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        resolver_name = self._to_pascal_case(name)
        resolver_snake = self._to_snake_case(name)
        context: dict[str, Any] = {
            "resolver_name": resolver_name,
            "resolver_name_snake": resolver_snake,
        }
        content = self.render_template("tenant_resolver.py.jinja2", context)
        file_path = self.output_dir / f"{resolver_snake}_tenant_resolver.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["TenantResolverGenerator"]
