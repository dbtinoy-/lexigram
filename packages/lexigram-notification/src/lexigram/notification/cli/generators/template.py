"""Notification template generator."""

from __future__ import annotations

from typing import Any

from lexigram.codegen.base import GenerationResult, GeneratorBase


class NotificationTemplateGenerator(GeneratorBase):
    """Generator for notification templates."""

    name = "notification_template"
    description = "Generate a notification template"
    default_output_dir = "src/notifications"

    def generate(self, name: str, **options: Any) -> GenerationResult:
        """Generate a notification template module.

        Args:
            name: Template name (e.g. ``"PasswordReset"``).
            **options: ``dry_run`` previews without writing; ``force``
                overwrites an existing file.

        Returns:
            A :class:`GenerationResult` describing the written file.
        """
        template_name = self._to_pascal_case(name)
        template_snake = self._to_snake_case(name)
        context = {
            "template_name": template_name,
            "template_name_snake": template_snake,
            "package_name": self._get_package_name(self.output_dir),
        }
        content = self.render_template("notification_template.py.jinja2", context)
        file_path = self.output_dir / f"{template_snake}_notification_template.py"
        if file_path.exists() and not options.get("force", False):
            return GenerationResult()
        if options.get("dry_run", False):
            return GenerationResult()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return GenerationResult(files_created=[file_path])
