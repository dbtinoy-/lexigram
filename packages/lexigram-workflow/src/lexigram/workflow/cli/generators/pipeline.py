"""Pipeline generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class PipelineGenerator(GeneratorBase):
    """Generator for pipeline definitions."""

    name = "pipeline"
    description = "Generate a pipeline with sequential processing stages"
    default_output_dir = "src/pipelines"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a pipeline module with sequential stages.

        Args:
            name: Pipeline name (e.g. ``"IngestETL"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        pipeline_name = self._to_pascal_case(name)
        pipeline_snake = self._to_snake_case(name)
        context = {
            "pipeline_name": pipeline_name,
            "pipeline_name_snake": pipeline_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("pipeline.py.jinja2", context)
        file_path = self.output_dir / f"{pipeline_snake}_pipeline.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
