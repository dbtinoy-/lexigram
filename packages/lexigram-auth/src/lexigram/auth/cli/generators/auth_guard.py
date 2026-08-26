"""Authentication guard generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class AuthGuardGenerator(GeneratorBase):
    """Generator for authentication guards."""

    name = "auth_guard"
    description = "Generate an authentication/authorization guard"
    default_output_dir = "src/guards"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate an authentication guard module.

        Args:
            name: Guard name (e.g. ``"ApiKey"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        guard_name = self._to_pascal_case(name)
        guard_snake = self._to_snake_case(name)
        context = {
            "guard_name": guard_name,
            "guard_name_snake": guard_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("auth_guard.py.jinja2", context)
        file_path = self.output_dir / f"{guard_snake}_auth_guard.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
