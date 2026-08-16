"""Message consumer generator for creating message queue consumers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class MessageConsumerGenerator(GeneratorBase):
    """Generator for creating message queue consumers."""

    name = "message_consumer"
    description = "Generate a message queue consumer"

    def __init__(
        self,
        output_dir: str | Path = "src/consumers",
        fields_str: str | None = None,
        **options: Any,
    ) -> None:
        super().__init__(output_dir=output_dir)
        self._fields_str = fields_str
        self._options = options

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a message consumer."""
        fields: list[FieldSpec] = []
        if self._fields_str:
            parsed = parse_fields(self._fields_str)
            if parsed:
                fields = parsed
        else:
            fields = [
                FieldSpec(name="message_type", type="str", required=True),
                FieldSpec(name="payload", type="dict", required=True),
            ]

        broker = self._options.get("broker", "redis")
        output_path = Path(str(self.output_dir))
        output_path.mkdir(parents=True, exist_ok=True)

        consumer_name = self._to_pascal_case(name)
        consumer_filename = f"{self._to_snake_case(name)}_consumer.py"

        context = {
            "consumer_name": consumer_name,
            "consumer_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(str(self.output_dir)),
            "fields": fields,
            "broker": broker,
            "queue_name": self._options.get("queue", name),
        }

        env = Environment(
            loader=PackageLoader("lexigram.cli", "templates"),
            autoescape=select_autoescape(),
        )

        template = env.get_template("message_consumer.py.jinja2")
        content = template.render(**context)

        file_path = output_path / consumer_filename
        if file_path.exists() and not self._options.get("force", False):
            return GenerationResult()

        with open(file_path, "w") as f:
            f.write(content)

        return GenerationResult(files_created=[file_path])
