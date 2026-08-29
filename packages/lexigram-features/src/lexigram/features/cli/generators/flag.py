"""Feature flag generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import GenerationResult, GeneratorBase
from lexigram.contracts.cli.generators import resolve_options


class FeatureFlagGenerator(GeneratorBase):
    """Generate a feature flag definition."""

    name = "feature_flag"
    description = "Generate a feature flag definition"
    default_output_dir = "src/features"

    def __init__(self, output_dir: str | Path = "src/features") -> None:
        super().__init__(output_dir=output_dir)

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **options: Any,
    ) -> GenerationResult:
        """Generate a feature flag definition module.

        Args:
            name: Flag name (e.g. ``"NewCheckout"`` or ``"new_checkout"``).
            dry_run: Compute output paths without writing.
            force: Overwrite an existing file.

        Returns:
            ``GenerationResult`` with created/skipped/overwritten paths.
        """
        flag_name = self._to_pascal_case(name)
        flag_snake = self._to_snake_case(name)
        context: dict[str, Any] = {
            "flag_name": flag_name,
            "flag_name_snake": flag_snake,
        }
        content = self.render_template("feature_flag.py.jinja2", context)
        file_path = self.output_dir / f"{flag_snake}_flag.py"
        self.stage(file_path, content)
        return self.finalize(self.commit(resolve_options(dry_run=dry_run, force=force)))


__all__ = ["FeatureFlagGenerator"]
