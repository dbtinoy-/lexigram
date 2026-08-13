"""Middleware generator for the web package."""

from __future__ import annotations

from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase


class MiddlewareGenerator(GeneratorBase):
    """Generate a middleware class."""

    template_name = "middleware.py.jinja2"

    def __init__(self, output_dir: str = "src/middleware") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        doc: str | None = None,
        options: dict[str, Any] | None = None,
        dry_run: bool = False,
        force: bool = False,
        **kwargs: object,
    ) -> GenerationResult:
        file_path = self.output_dir / f"{self._to_snake_case(name)}_middleware.py"
        content = self.render_template(
            self.template_name,
            {
                "name": name,
                "class_name": f"{self._to_pascal_case(name)}Middleware",
                "doc": doc,
                "options": options,
            },
        )
        return self.write_file(file_path, content, dry_run=dry_run, force=force)


__all__ = ["MiddlewareGenerator"]
