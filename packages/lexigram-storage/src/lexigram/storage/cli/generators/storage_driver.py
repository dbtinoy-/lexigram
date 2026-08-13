"""Storage driver generator for creating custom storage backends."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase, parse_fields


class StorageDriverGenerator(GeneratorBase):
    """Generator for creating custom storage drivers."""

    name = "storage_driver"
    description = "Generate a custom storage driver"
    default_output_dir = "src/storage/backends"

    def __init__(self, output_dir: str = "src/storage/backends") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        output_dir: str | None = None,
        fields_str: str | None = None,
        **options: Any,
    ) -> GenerationResult:
        """Generate a storage driver."""
        fields = parse_fields(fields_str) if fields_str else []
        driver_type = options.get("driver_type", "local")
        is_async = bool(options.get("async", False))
        dry_run = bool(options.get("dry_run", False))
        force = bool(options.get("force", False))

        output_path = Path(output_dir) if output_dir is not None else self.output_dir
        file_path = output_path / f"{self._to_snake_case(name)}.py"
        if file_path.exists() and not force:
            return GenerationResult()

        content = self.render_template(
            "storage_driver.py.jinja2",
            {
                "driver_name": self._to_pascal_case(name),
                "driver_name_snake": self._to_snake_case(name),
                "package_name": self._get_package_name(output_path),
                "fields": fields,
                "driver_type": driver_type,
                "is_async": is_async,
            },
        )

        if not dry_run:
            output_path.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        return GenerationResult(files_created=[output_path])

    @staticmethod
    def _get_package_name(output_dir: str | Path) -> str:
        parts = Path(output_dir).parts
        if parts and parts[0] == "src":
            parts = parts[1:]
        return ".".join(parts) if parts else "app"


__all__ = ["StorageDriverGenerator"]
