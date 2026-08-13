"""WebSocket handler generator for the web package."""

from __future__ import annotations

from lexigram.codegen import GenerationResult, GeneratorBase


class WebSocketHandlerGenerator(GeneratorBase):
    """Generate a WebSocket handler scaffold."""

    name = "websocket"
    description = "Generate a WebSocket handler for real-time communication"
    default_output_dir = "src/websocket"

    def __init__(self, output_dir: str = "src/websocket") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: object,
    ) -> GenerationResult:
        snake_name = self._to_snake_case(name)
        file_path = self.output_dir / f"{snake_name}.py"
        content = self.render_template(
            "websocket.py.jinja2",
            {
                "name": self._to_pascal_case(name),
                "snake_name": snake_name,
                "snake_name_plural": f"{snake_name}s",
            },
        )
        return self.write_file(file_path, content, dry_run=dry_run, force=force)


__all__ = ["WebSocketHandlerGenerator"]
