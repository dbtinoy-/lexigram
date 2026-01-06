"""DataLoaderProtocol Generator for Lexigram CLI.

Generates DataLoaderProtocol classes for GraphQL to solve N+1 query problems.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

from lexigram.codegen.base import GenerationResult, GeneratorBase


class DataLoaderGenerator(GeneratorBase):
    """Generator for GraphQL DataLoaders.

    Creates DataLoaderProtocol classes that batch and cache data fetches
    to efficiently resolve GraphQL queries.
    """

    name = "dataloader"
    description = "Generate a GraphQL DataLoaderProtocol to solve N+1 problems"
    default_output_dir = "src/graphql/dataloaders"

    def __init__(self, output_dir: str = "src/graphql/dataloaders") -> None:
        template_dir = Path(__file__).parent.parent / "templates"
        super().__init__(
            output_dir=output_dir,
            template_root=template_dir,
        )
        self._jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def generate(
        self,
        name: str,
        output_dir: str = "src/graphql/dataloaders",
        key_type: str = "str",
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a DataLoaderProtocol.

        Args:
            name: Name of the DataLoaderProtocol (e.g., "UserLoader")
            output_dir: Directory to write the file
            key_type: Type of the key (e.g., "str", "int")

        Returns:
            GeneratorResult with generated file path
        """
        snake_name = self._to_snake_case(name)
        output_path = Path(output_dir) / f"{snake_name}.py"

        template = self._jinja_env.get_template("dataloader.py.jinja2")
        rendered = template.render(
            name=name,
            snake_name=snake_name,
            key_type=key_type,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered)

        return GenerationResult(files_created=[output_path])
