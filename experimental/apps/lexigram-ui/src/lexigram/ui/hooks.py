"""Root hook payload surface for lexigram-ui.

Defines canonical payload dataclasses for server-rendered UI component hook
points. Actual hook registration and invocation use the framework's
string-keyed ``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "UIComponentRenderedHook",
    "UITemplateRenderedHook",
]


@dataclass(frozen=True, kw_only=True)
class UIComponentRenderedHook:
    """Payload fired after a UI component completes rendering.

    Attributes:
        component_name: Qualified name of the component class that rendered.
    """

    component_name: str


@dataclass(frozen=True, kw_only=True)
class UITemplateRenderedHook:
    """Payload fired after a template is rendered to its final HTML output.

    Attributes:
        template_name: Name or path of the template that was rendered.
    """

    template_name: str
