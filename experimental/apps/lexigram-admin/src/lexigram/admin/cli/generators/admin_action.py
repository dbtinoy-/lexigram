"""Admin action generator for creating custom admin UI actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class AdminActionGenerator(GeneratorBase):
    """Generate a custom admin UI action."""

    name = "admin_action"
    description = "Generate a custom admin action"
    default_output_dir = "src/admin/actions"

    def __init__(self, output_dir: str | Path = "src/admin/actions") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate an admin action module.

        Args:
            name: Action name (e.g. ``"Approve"`` or ``"approve"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        action_type = str(options.get("type", "row"))
        target = str(options.get("target", "dialog"))

        action_name = self._to_pascal_case(name)
        file_path = self.output_dir / f"{self._to_snake_case(name)}_action.py"

        context: dict[str, Any] = {
            "action_name": action_name,
            "action_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.output_dir),
            "action_type": action_type,
            "target": target,
        }
        content = self.render_template("admin_action.py.jinja2", context)
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["AdminActionGenerator"]
