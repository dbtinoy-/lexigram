"""Metric generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class MetricGenerator(GeneratorBase):
    """Generator for custom metric definitions."""

    name = "metric"
    description = "Generate a custom metric definition with backend registration"
    default_output_dir = "src/metrics"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a custom metric definition module.

        Args:
            name: Metric name (e.g. ``"OrderLatency"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        metric_name = self._to_pascal_case(name)
        metric_snake = self._to_snake_case(name)
        context = {
            "metric_name": metric_name,
            "metric_name_snake": metric_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("metric.py.jinja2", context)
        file_path = self.output_dir / f"{metric_snake}_metric.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
