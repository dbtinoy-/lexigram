"""API client generator for creating external API client wrappers."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class APIClientGenerator(GeneratorBase):
    """Generator for creating external API client wrappers."""

    name = "api_client"
    description = "Generate an external API client"
    default_output_dir = "src/clients"

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        normalized = APIClientGenerator._to_snake_case(name)
        return "".join(part.capitalize() for part in normalized.split("_") if part)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        compact = re.sub(r"[\s-]+", "_", name)
        separated = re.sub(r"([A-Z])", r"_\1", compact)
        return separated.lower().strip("_")

    def generate(
        self,
        name: str,
        output_dir: str = "src/clients",
        fields_str: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        """Generate an API client."""
        # Parse fields if provided (API methods)
        fields = []
        if fields_str:
            fields = parse_fields(fields_str)
        else:
            # Default fields for a basic client
            fields = [
                FieldSpec(name="base_url", type="str", required=True),
                FieldSpec(name="api_key", type="str", required=False),
            ]

        # Determine auth type
        auth_type = options.get("auth", "apikey")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Client class name
        client_name = self._to_pascal_case(name)
        client_filename = f"{self._to_snake_case(name)}_client.py"

        # Template context
        context = {
            "client_name": client_name,
            "client_name_snake": self._to_snake_case(name),
            "package_name": self._get_package_name(output_dir),
            "fields": fields,
            "auth_type": auth_type,
        }

        # Render template
        env = Environment(
            loader=PackageLoader("lexigram.cli", "templates"),
            autoescape=select_autoescape(),
        )

        template = env.get_template("api_client.py.jinja2")
        content = template.render(**context)

        # Write file
        file_path = output_path / client_filename
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()

        with open(file_path, "w") as f:
            f.write(content)

        return GenerationResult(files_created=[output_path])
