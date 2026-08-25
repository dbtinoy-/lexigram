from __future__ import annotations

from typing import Any

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class CommandHandlerGenerator(GeneratorBase):
    name = "command"
    description = "Generate a command handler (CQRS)"
    default_output_dir = "src/commands"

    def generate(
        self,
        name: str,
        fields_str: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        fields: list[FieldSpec] = []
        if fields_str:
            fields = parse_fields(fields_str)
        else:
            fields = [FieldSpec(name="id", type="str", required=False)]

        output_path = self.output_dir
        command_name = self._to_pascal_case(name)
        command_filename = f"{self._to_snake_case(name)}.py"

        context = {
            "command_name": command_name,
            "command_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.output_dir),
            "fields": fields,
        }

        content = self.render_template("command_handler.py.jinja2", context)

        file_path = output_path / command_filename
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()

        if not options.get("dry_run", False):
            output_path.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return GenerationResult(files_created=[file_path])

        return GenerationResult()
