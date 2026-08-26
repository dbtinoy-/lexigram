"""Saga step generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class SagaStepGenerator(GeneratorBase):
    """Generator for saga steps with compensating transactions."""

    name = "saga_step"
    description = "Generate a saga step with compensating transaction"
    default_output_dir = "src/sagas"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a saga step module.

        Args:
            name: Step name (e.g. ``"ReserveInventory"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        step_name = self._to_pascal_case(name)
        step_snake = self._to_snake_case(name)
        context = {
            "step_name": step_name,
            "step_name_snake": step_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("saga_step.py.jinja2", context)
        file_path = self.output_dir / f"{step_snake}_saga_step.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
