from __future__ import annotations

from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class QueryHandlerGenerator(GeneratorBase):
    name = "query"
    description = "Generate a query handler (CQRS)"
    default_output_dir = "src/queries"

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
        query_name = self._to_pascal_case(name)
        query_filename = f"{self._to_snake_case(name)}.py"

        context = {
            "query_name": query_name,
            "query_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.output_dir),
            "fields": fields,
        }

        env = Environment(
            loader=PackageLoader("lexigram.events.cli", "templates"),
            autoescape=select_autoescape(),
        )
        template = env.get_template("query_handler.py.jinja2")
        content = template.render(**context)

        file_path = output_path / query_filename
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()

        if not options.get("dry_run", False):
            output_path.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return GenerationResult(files_created=[file_path])

        return GenerationResult()
