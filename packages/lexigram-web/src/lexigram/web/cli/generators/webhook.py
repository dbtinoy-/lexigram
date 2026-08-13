"""Webhook generator for the web package."""

from __future__ import annotations

from lexigram.codegen import GenerationResult, GeneratorBase, parse_fields


class WebhookGenerator(GeneratorBase):
    """Generate a webhook handler scaffold."""

    name = "webhook"
    description = "Generate a webhook handler"
    default_output_dir = "src/webhooks"

    def __init__(self, output_dir: str = "src/webhooks") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        fields_str: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: object,
    ) -> GenerationResult:
        file_path = self.output_dir / f"{self._to_snake_case(name)}_webhook.py"
        content = self.render_template(
            "webhook.py.jinja2",
            {
                "webhook_name": self._to_pascal_case(name),
                "webhook_name_snake": self._to_snake_case(name),
                "package_name": self._package_name(),
                "fields": parse_fields(fields_str or ""),
            },
        )
        return self.write_file(file_path, content, dry_run=dry_run, force=force)

    def _package_name(self) -> str:
        parts = self.output_dir.parts
        if parts[:1] == ("src",):
            parts = parts[1:]
        return ".".join(parts) if parts else "app"


__all__ = ["WebhookGenerator"]
