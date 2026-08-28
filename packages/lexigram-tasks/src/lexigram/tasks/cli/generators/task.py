"""Task generator for the Lexigram CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase, parse_fields
from lexigram.contracts.cli.generators import resolve_options


class TaskGenerator(GeneratorBase):
    """Generate a background task."""

    name = "task"
    description = "Generate a background task with queue registration"
    default_output_dir = "src/tasks"

    def __init__(self, output_dir: str | Path = "src/tasks") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a task file.

        Args:
            name: The name of the task (e.g. ``"ProcessData"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        fields_str: str | None = options.get("fields_str")
        params_str: str | None = options.get("params_str")
        doc: str | None = options.get("doc")
        schedule: str | None = options.get("schedule")
        package_name: str = str(options.get("package_name", "app"))

        task_name = self._to_snake_case(name)
        fields = parse_fields(fields_str or "")

        # Parse params from params_str (format: "name:type=default,...")
        params = self._parse_params(params_str or "")

        context: dict[str, Any] = {
            "name": name,
            "class_name": self._to_pascal_case(name),
            "task_name": task_name,
            "resource_name": task_name,
            "doc": doc,
            "schedule": schedule,
            "package_name": package_name,
            "params": params
            or [
                {
                    "name": "id",
                    "type": "int",
                    "default": "None",
                    "description": "The item ID",
                },
            ],
            "fields": [
                {"name": f.name, "type": f.type, "required": f.required} for f in fields
            ],
        }
        content = self.render_template("task.py.jinja2", context)
        file_path = self.output_dir / f"{task_name}_task.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))

    @staticmethod
    def _parse_params(params_str: str) -> list[dict[str, str]]:
        """Parse ``name:type=default,...`` into param dicts."""
        params: list[dict[str, str]] = []
        for raw_param in params_str.split(","):
            param_def = raw_param.strip()
            if not param_def:
                continue
            if "=" in param_def:
                param_name, param_default = param_def.split("=", 1)
                param_type = "Any"
            else:
                param_name = param_def
                param_default = "None"
                param_type = "Any"
            params.append(
                {
                    "name": param_name.strip(),
                    "type": param_type,
                    "default": param_default.strip(),
                    "description": f"The {param_name.strip()} parameter",
                },
            )
        return params


__all__ = ["TaskGenerator"]
