from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class EventGenerator(GeneratorBase):
    template_name = "event.py.jinja2"

    def __init__(self, output_dir: str = "src/events") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(
        self,
        name: str,
        fields_str: str | None = None,
        doc: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        result = GenerationResult()
        event_name = self._to_snake_case(name)
        file_path = self.output_dir / f"{event_name}_event.py"

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        fields = parse_fields(fields_str or "")
        resource_name = event_name
        if resource_name.endswith("y"):
            resource_name = resource_name[:-1] + "ies"
        elif not resource_name.endswith("s"):
            resource_name = resource_name + "s"

        context: dict[str, Any] = {
            "name": name,
            "class_name": name,
            "resource_name": resource_name,
            "doc": doc,
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
