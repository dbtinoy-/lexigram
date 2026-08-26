"""Saga generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class SagaGenerator(GeneratorBase):
    """Generator for saga orchestrators."""

    name = "saga"
    description = "Generate a saga orchestrator with compensating actions"
    default_output_dir = "src/sagas"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a saga orchestrator module.

        Args:
            name: Saga name (e.g. ``"OrderFulfillment"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        saga_name = self._to_pascal_case(name)
        saga_snake = self._to_snake_case(name)
        context = {
            "saga_name": saga_name,
            "saga_name_snake": saga_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("saga.py.jinja2", context)
        file_path = self.output_dir / f"{saga_snake}_saga.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
