"""Shared Jinja2 renderer for lexigram-queue admin widgets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

from lexigram.logging import get_logger

logger = get_logger(__name__)
_TEMPLATES_PATH = Path(__file__).parent / "widgets" / "templates"


class PackageWidgetRenderer:
    """Renders admin widget templates for lexigram-queue. Singleton."""

    def __init__(self) -> None:
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_TEMPLATES_PATH)),
            autoescape=True,
            auto_reload=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template. Raises jinja2.TemplateNotFound on misconfiguration.

        Args:
            template_name: Template filename (e.g. "queue_depth.html").
            context: Context dict for template variables.

        Returns:
            Rendered HTML string.

        Raises:
            jinja2.TemplateNotFound: If template does not exist.
        """
        return self._env.get_template(template_name).render(**context)


__all__ = ["PackageWidgetRenderer"]
