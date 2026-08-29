"""DataLoaderProtocol Generator for Lexigram CLI.

Generates DataLoaderProtocol classes for GraphQL to solve N+1 query problems.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class DataLoaderGenerator(GeneratorBase):
    """Generate a GraphQL DataLoader.

    Creates DataLoaderProtocol classes that batch and cache data fetches
    to efficiently resolve GraphQL queries.
    """

    name = "dataloader"
    description = "Generate a GraphQL DataLoaderProtocol to solve N+1 problems"
    default_output_dir = "src/schema/dataloaders"

    def __init__(self, output_dir: str | Path = "src/schema/dataloaders") -> None:
        super().__init__(output_dir=output_dir)

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def generate(
        self,
        name: str,
        *,
        key_type: str = "str",
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a DataLoader module.

        Args:
            name: Name of the DataLoader (e.g. ``"UserLoader"`` or ``"user_loader"``).
            key_type: Type of the key (e.g. ``"str"``, ``"int"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        snake_name = self._to_snake_case(name)
        content = self.render_template(
            "dataloader.py.jinja2",
            {
                "name": name,
                "snake_name": snake_name,
                "key_type": key_type,
            },
        )
        file_path = self.output_dir / f"{snake_name}.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["DataLoaderGenerator"]
