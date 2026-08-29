"""Event handler generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class EventHandlerGenerator(GeneratorBase):
    """Generate an event handler with bus registration.

    The emitted handler follows the convention demonstrated in
    ``demos/event-driven-orders``: ``on_<event_type>`` methods that the
    event bus subscribes to explicitly during provider boot.
    """

    name = "event_handler"
    description = "Generate an event handler with bus registration"
    default_output_dir = "src/handlers"

    def __init__(self, output_dir: str | Path = "src/handlers") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate an event handler module.

        Args:
            name: Handler name, e.g. ``"OrderPlaced"`` or ``"order_placed"``.
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        handler_name = self._to_pascal_case(name)
        handler_snake = self._to_snake_case(name)
        context: dict[str, Any] = {
            "handler_name": handler_name,
            "event_name": handler_snake,
        }
        content = self.render_template("event_handler.py.jinja2", context)
        file_path = self.output_dir / f"{handler_snake}_handler.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["EventHandlerGenerator"]
