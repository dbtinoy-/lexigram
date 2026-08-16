"""Task generator for the Lexigram CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class TaskGenerator(GeneratorBase):
    """Generates a background task."""

    template_name = "task.py.jinja2"

    def __init__(self, output_dir: str = "src/tasks") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(
        self,
        name: str,
        **options: Any,
    ) -> GenerationResult:
        """Generate a task file.

        Args:
            name: The name of the task (e.g., "ProcessData").

        Returns:
            GenerationResult with created/skipped files.
        """
        fields_str: str | None = options.get("fields_str")
        params_str: str | None = options.get("params_str")
        doc: str | None = options.get("doc")
        schedule: str | None = options.get("schedule")
        package_name: str = options.get("package_name", "app")
        dry_run: bool = options.get("dry_run", False)
        force: bool = options.get("force", False)

        result = GenerationResult()

        task_name = self._to_snake_case(name)
        file_path = self.output_dir / f"{task_name}_task.py"

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        fields = parse_fields(fields_str or "")

        # Parse params from params_str (format: "name:type=default,...")
        params = []
        if params_str:
            for raw_param in params_str.split(","):
                param_def = raw_param.strip()
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
                        "description": f"The {param_name} parameter",
                    },
                )

        # Determine resource name
        resource_name = task_name

        context: dict[str, Any] = {
            "name": name,
            "class_name": name,
            "resource_name": resource_name,
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

        template = self.env.get_template(self.template_name)
        content = template.render(**context)

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            if file_path.exists() and force:
                result.files_overwritten.append(file_path)
            else:
                result.files_created.append(file_path)

        return result
