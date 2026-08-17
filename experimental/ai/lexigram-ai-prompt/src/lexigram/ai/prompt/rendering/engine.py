"""Prompt rendering engine — f-string (default) with optional Jinja2 support."""

from __future__ import annotations

from enum import StrEnum
import re
from string import Template
from typing import Any

from lexigram.ai.prompt.exceptions import PromptRenderError


class RenderFormat(StrEnum):
    """Supported template substitution formats."""

    F_STRING = "f_string"
    """``{variable_name}`` style (default)."""
    JINJA2 = "jinja2"
    """Jinja2 ``{{ variable_name }}`` style (requires ``jinja2`` extra)."""
    DOLLAR = "dollar"
    """``$variable_name`` / ``${variable_name}`` style (stdlib ``string.Template``)."""
    SIMPLE = "simple"
    """Literal template — no substitution performed."""


class PromptRenderer:
    """Renders a template string by substituting named variables.

    Supports three formats controlled by :class:`RenderFormat`.

    Args:
        format: Substitution format.  Defaults to :attr:`RenderFormat.F_STRING`.
    """

    def __init__(self, format: RenderFormat = RenderFormat.F_STRING) -> None:
        self._format = format

    @property
    def format(self) -> RenderFormat:
        """The active rendering format."""
        return self._format

    def render(self, template: str, variables: dict[str, Any]) -> str:
        """Substitute *variables* into *template*.

        Args:
            template: Raw template string.
            variables: Variable name → value mapping.

        Returns:
            Rendered string.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
                A required placeholder has no matching variable.
        """
        try:
            if self._format == RenderFormat.SIMPLE:
                return template
            if self._format == RenderFormat.JINJA2:
                return self._render_jinja2(template, variables)
            if self._format == RenderFormat.DOLLAR:
                return Template(template).substitute(variables)
            # F_STRING (default)
            return template.format_map(_DefaultFormatMap(variables))
        except PromptRenderError:
            raise
        except KeyError as exc:
            raise PromptRenderError(f"Missing variable {exc} in template.") from exc
        except ValueError as exc:
            raise PromptRenderError(str(exc)) from exc

    @staticmethod
    def _render_jinja2(template: str, variables: dict[str, Any]) -> str:
        """Render a Jinja2 template string."""
        try:
            from jinja2 import StrictUndefined
            from jinja2 import Template as Jinja2Template
            from jinja2.exceptions import TemplateError
        except ImportError as exc:
            raise PromptRenderError(
                "Jinja2 is not installed. Add the 'jinja2' extra: "
                "pip install lexigram-ai-platform[jinja2]"
            ) from exc
        try:
            tmpl = Jinja2Template(template, undefined=StrictUndefined)
            return tmpl.render(**variables)
        except TemplateError as exc:
            raise PromptRenderError(str(exc)) from exc

    def get_variables(self, template: str) -> list[str]:
        """Extract placeholder names from *template*.

        Args:
            template: Raw template string.

        Returns:
            Unique list of variable names detected in the template.
        """
        if self._format == RenderFormat.SIMPLE:
            return []
        if self._format == RenderFormat.JINJA2:
            # Find {{ var }} style (simple names only — not expressions)
            return list(dict.fromkeys(re.findall(r"\{\{\s*(\w+)\s*\}\}", template)))
        if self._format == RenderFormat.DOLLAR:
            return list(dict.fromkeys(re.findall(r"\$\{?(\w+)\}?", template)))
        # F_STRING
        return list(dict.fromkeys(re.findall(r"\{(\w+)\}", template)))


class _DefaultFormatMap(dict):
    """``str.format_map`` helper that raises ``KeyError`` for missing keys."""

    def __missing__(self, key: str) -> str:
        raise KeyError(key)


__all__ = ["PromptRenderer", "RenderFormat"]
