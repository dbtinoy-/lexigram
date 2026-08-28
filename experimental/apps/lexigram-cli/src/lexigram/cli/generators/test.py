"""Test generator for the Lexigram CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.cli.generators.base import GenerationResult, GeneratorBase
from lexigram.cli.generators.field_parser import parse_fields
from lexigram.cli.lib import to_snake_case

# Sample values for different field types
FIELD_SAMPLE_VALUES = {
    "str": '"sample_string"',
    "string": '"sample_string"',
    "text": '"sample text"',
    "int": "1",
    "integer": "1",
    "float": "1.5",
    "bool": "True",
    "boolean": "True",
    "datetime": "datetime(2024, 1, 1, tzinfo=UTC)",
}


class TestGenerator(GeneratorBase):
    """Generates a test file for models, services, or controllers."""

    template_name = "test_unit.py.jinja2"

    def __init__(self, output_dir: str = "tests/unit") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(
        self,
        name: str,
        test_type: str = "model",
        fields_str: str | None = None,
        package_name: str | None = "app",
        doc: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a test file.

        Args:
            name: The name of the module/class to test (e.g., "User").
            test_type: Type of test (model, service, controller).
            fields_str: Field specifications for test data.
            package_name: The package name for imports.
            doc: Test documentation.
            dry_run: If True, don't write files.
            force: If True, overwrite existing files.

        Returns:
            GenerationResult with created/skipped files.
        """
        result = GenerationResult()

        model_name = to_snake_case(name)
        file_path = self.output_dir / f"test_{model_name}.py"

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        fields = parse_fields(fields_str or "")

        # Determine resource name
        resource_name = model_name
        if resource_name.endswith("y"):
            resource_name = resource_name[:-1] + "ies"
        elif not resource_name.endswith("s"):
            resource_name = resource_name + "s"

        # Prepare fields with sample values
        prepared_fields = []
        for field in fields:
            prepared_fields.append(
                {
                    "name": field.name,
                    "type": field.type,
                    "required": field.required,
                    "sample_value": FIELD_SAMPLE_VALUES.get(field.type, '"sample"'),
                },
            )

        # If no fields provided, add some defaults
        if not prepared_fields:
            prepared_fields = [
                {
                    "name": "name",
                    "type": "str",
                    "required": True,
                    "sample_value": '"Test"',
                },
                {
                    "name": "email",
                    "type": "str",
                    "required": True,
                    "sample_value": '"test@example.com"',
                },
                {
                    "name": "active",
                    "type": "bool",
                    "required": False,
                    "sample_value": "True",
                },
            ]

        context: dict[str, Any] = {
            "name": name,
            "class_name": name,
            "model_name": model_name,
            "resource_name": resource_name,
            "test_type": test_type,
            "package_name": package_name,
            "doc": doc,
            "fields": prepared_fields,
        }

        template = self.env.get_template(self.template_name)
        content = template.render(**context)

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            if file_path.exists() and force:
                result.files_overwritten.append(file_path)
            else:
                result.files_created.append(file_path)

        return result
