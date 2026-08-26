"""Workflow definition generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class WorkflowDefinitionGenerator(GeneratorBase):
    """Generator for workflow definitions."""

    name = "workflow_def"
    description = "Generate a workflow definition with steps and transitions"
    default_output_dir = "src/workflows"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a workflow definition module.

        Args:
            name: Workflow name (e.g. ``"OrderProcessing"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        workflow_name = self._to_pascal_case(name)
        workflow_snake = self._to_snake_case(name)
        context = {
            "workflow_name": workflow_name,
            "workflow_name_snake": workflow_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("workflow_def.py.jinja2", context)
        file_path = self.output_dir / f"{workflow_snake}_workflow.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
