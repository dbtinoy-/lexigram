"""Message consumer generator for creating message queue consumers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
        self._options: dict[str, Any] = options

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Render the consumer template, then write it — in that order.

        Template rendering happens before any filesystem mutation so a bad
        context or missing template leaves no directories behind.
        """
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

        merged_options: dict[str, Any] = {**self._options, **options}
        broker = merged_options.get("broker", "redis")
        consumer_name = self._to_pascal_case(name)
        context = {
            "consumer_name": consumer_name,
            "consumer_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.raw_output_dir),
            "fields": fields,
            "broker": broker,
            "queue_name": merged_options.get("queue", name),
        }

        content = self.render_template("message_consumer.py.jinja2", context)

        consumer_filename = f"{self._to_snake_case(name)}_consumer.py"
        file_path = Path(self.output_dir) / consumer_filename
        return self.write_file(
            file_path, content, force=bool(merged_options.get("force", False))
        )
