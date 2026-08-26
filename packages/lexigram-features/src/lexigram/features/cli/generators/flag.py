"""Feature flag generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class FeatureFlagGenerator(GeneratorBase):
    """Generator for feature flag definitions."""

    name = "feature_flag"
    description = "Generate a feature flag definition"
    default_output_dir = "src/features"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a feature flag definition module.

        Args:
            name: Flag name (e.g. ``"NewCheckout"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        flag_name = self._to_pascal_case(name)
        flag_snake = self._to_snake_case(name)
        context = {
            "flag_name": flag_name,
            "flag_name_snake": flag_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("feature_flag.py.jinja2", context)
        file_path = self.output_dir / f"{flag_snake}_flag.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
