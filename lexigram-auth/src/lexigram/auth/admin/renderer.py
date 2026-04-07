"""Jinja2 widget renderer for auth admin widgets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

_TEMPLATES_PATH = Path(__file__).parent / "widgets" / "templates"


class PackageWidgetRenderer:
    """Renders admin widget templates for lexigram-auth.

    Singleton — one Jinja2 env per process.
    """

    def __init__(self) -> None:
        """Initialize renderer with the package templates directory."""
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_TEMPLATES_PATH)),
            autoescape=True,
            auto_reload=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with context.

        Args:
            template_name: Name of the template file (e.g., "active_sessions.html").
            context: Context variables for the template.

        Returns:
            Rendered HTML string.

        Raises:
            jinja2.TemplateNotFound: If template does not exist.
        """
        return self._env.get_template(template_name).render(**context)


__all__ = ["PackageWidgetRenderer"]
