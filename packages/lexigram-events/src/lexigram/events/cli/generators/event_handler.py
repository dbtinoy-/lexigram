"""Event handler generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class EventHandlerGenerator(GeneratorBase):
    """Generator for event handlers."""

    name = "event_handler"
    description = "Generate an event handler with bus registration"
    default_output_dir = "src/handlers"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate an event handler module.

        Args:
            name: Handler name (e.g. ``"OrderPlaced"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        handler_name = self._to_pascal_case(name)
        handler_snake = self._to_snake_case(name)
        context = {
            "handler_name": handler_name,
            "handler_name_snake": handler_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("event_handler.py.jinja2", context)
        file_path = self.output_dir / f"{handler_snake}_handler.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
