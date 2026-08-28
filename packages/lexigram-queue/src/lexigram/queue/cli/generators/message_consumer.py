"""Message consumer generator for creating message queue consumers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import FieldSpec, GenerationResult, GeneratorBase, parse_fields
from lexigram.contracts.cli.generators import resolve_options


class MessageConsumerGenerator(GeneratorBase):
    """Generate a message queue consumer."""

    name = "message_consumer"
    description = "Generate a message queue consumer with routing"
    default_output_dir = "src/consumers"

    def __init__(
        self,
        output_dir: str | Path = "src/consumers",
        fields_str: str | None = None,
        **options: Any,
    ) -> None:
        super().__init__(output_dir=output_dir)
        self._fields_str = fields_str
        self._options = dict(options)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a message consumer module.

        Args:
            name: Consumer name (e.g. ``"OrderEvents"`` or ``"order_events"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        fields: list[FieldSpec]
        if self._fields_str:
            parsed = parse_fields(self._fields_str)
            fields = parsed if parsed else self._default_fields()
        else:
            fields = self._default_fields()

        merged_options: dict[str, Any] = {**self._options, **options}
        broker = merged_options.get("broker", "redis")
        consumer_name = self._to_pascal_case(name)
        context: dict[str, Any] = {
            "consumer_name": consumer_name,
            "consumer_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(self.raw_output_dir),
            "fields": fields,
            "broker": broker,
            "queue_name": merged_options.get("queue", name),
        }
        content = self.render_template("message_consumer.py.jinja2", context)
        file_path = Path(self.output_dir) / f"{self._to_snake_case(name)}_consumer.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))

    @staticmethod
    def _default_fields() -> list[FieldSpec]:
        """Return the default payload fields for a consumer."""
        return [
            FieldSpec(name="message_type", type="str", required=True),
            FieldSpec(name="payload", type="dict", required=True),
        ]


__all__ = ["MessageConsumerGenerator"]
