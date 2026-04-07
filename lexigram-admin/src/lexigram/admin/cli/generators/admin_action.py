"""Admin action generator for creating custom admin UI actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class AdminActionGenerator(GeneratorBase):
    """Generator for creating custom admin UI actions."""

    name = "admin_action"
    description = "Generate a custom admin action"
    default_output_dir = "src/admin/actions"

    def __init__(self, output_dir: str = "src/admin/actions") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(
        self,
        name: str,
        **options: Any,
    ) -> GenerationResult:
        """Generate an admin action."""
        action_type = options.get("type", "row")
        target = options.get("target", "dialog")
        dry_run = bool(options.get("dry_run", False))
        force = bool(options.get("force", False))

        action_name = name.capitalize()
        action_filename = f"{self._to_snake_case(name)}_action.py"
        file_path = self.output_dir / action_filename

        if file_path.exists() and not force:
            return GenerationResult(files_skipped=[file_path])

        context = {
            "action_name": action_name,
            "action_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.output_dir),
            "action_type": action_type,
            "target": target,
        }

        content = self.render_template("admin_action.py.jinja2", context)

        if dry_run:
            return GenerationResult(files_created=[file_path])

        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

        return GenerationResult(files_created=[file_path])
