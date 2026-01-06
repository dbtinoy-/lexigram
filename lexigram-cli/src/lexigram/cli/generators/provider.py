"""Provider generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.cli.generators.base import GenerationResult, GeneratorBase
from lexigram.cli.lib import to_snake_case


class ProviderGenerator(GeneratorBase):
    """Generates a provider class."""

    def __init__(self, output_dir: str = "src") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(  # type: ignore[override]
        self,
        name: str,
        doc: str | None = None,
        config_options: list[dict[str, Any]] | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a provider file.

        Args:
            name: The name of the provider (e.g., "User").
            doc: Provider documentation.
            config_options: List of configuration option definitions.
            dry_run: If True, don't write files.
            force: If True, overwrite existing files.

        Returns:
            GenerationResult with created/skipped files.
        """
        result = GenerationResult()

        # Strip "Provider" suffix if the user included it (e.g. "ChatProvider" -> "Chat")
        base_name = name
        if base_name.endswith("Provider"):
            base_name = base_name[:-8]
        provider_name = to_snake_case(base_name)
        file_path = self.output_dir / f"{provider_name}_provider.py"

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        # Determine resource name
        resource_name = provider_name
        if resource_name.endswith("y"):
            resource_name = resource_name[:-1] + "ies"
        elif not resource_name.endswith("s"):
            resource_name = resource_name + "s"

        # Convert to PascalCase for class name
        class_name = "".join(word.capitalize() for word in provider_name.split("_"))

        context: dict[str, Any] = {
            "name": name,
            "class_name": class_name,
            "resource_name": resource_name,
            "doc": doc,
            "config_options": config_options,
        }

        template = self.env.get_template("provider.py.jinja2")
        content = template.render(**context)

        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            if file_path.exists() and force:
                result.files_overwritten.append(file_path)
            else:
                result.files_created.append(file_path)

        return result
