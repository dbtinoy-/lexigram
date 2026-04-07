"""Widget renderer for web admin dashboard.

Provides a Jinja2-based renderer for admin widgets. One singleton renderer
per package, loads templates from the widgets/templates/ directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

_TEMPLATES_PATH = Path(__file__).parent / "widgets" / "templates"


class PackageWidgetRenderer:
    """Jinja2-based renderer for web admin widgets.

    Singleton instance that manages a Jinja2 environment for rendering
    widget templates. Templates are loaded from lexigram/web/admin/widgets/templates/.

    The environment uses autoescape=True for security and auto_reload=False
    for production stability.
    """

    def __init__(self) -> None:
        """Initialize renderer with Jinja2 environment."""
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_TEMPLATES_PATH)),
            autoescape=True,
            auto_reload=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a widget template with the given context.

        Args:
            template_name: Filename of the template (e.g., "server_status.html").
            context: Dictionary of variables to pass to the template.

        Returns:
            Rendered HTML string.

        Raises:
            jinja2.TemplateNotFound: If the template does not exist.
        """
        return self._env.get_template(template_name).render(**context)


__all__ = ["PackageWidgetRenderer"]
