"""Authorization policy generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class AuthPolicyGenerator(GeneratorBase):
    """Generator for authorization policies."""

    name = "auth_policy"
    description = "Generate an authorization policy"
    default_output_dir = "src/policies"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate an authorization policy module.

        Args:
            name: Policy name (e.g. ``"ProjectAccess"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        policy_name = self._to_pascal_case(name)
        policy_snake = self._to_snake_case(name)
        context = {
            "policy_name": policy_name,
            "policy_name_snake": policy_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("auth_policy.py.jinja2", context)
        file_path = self.output_dir / f"{policy_snake}_policy.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
