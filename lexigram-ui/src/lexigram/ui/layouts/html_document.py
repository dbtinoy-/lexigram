"""HTML Document base class.

Provides the fundamental HTML document structure that all layouts inherit from.
Handles DOCTYPE, html, head, and body with common meta tags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from markupsafe import Markup, escape

from lexigram.ui.config import HTMLDocumentConfig


class HTMLDocument(ABC):
    """Abstract base class for HTML document generation.

    Provides the basic HTML5 document structure that all layouts build upon.
    Subclasses implement render_head_content(), render_body_content(),
    and render_body_end() to customize the document.

    Features:
    - DOCTYPE html5
    - Configurable lang, charset, meta tags
    - Extensible head and body sections
    - Escape-safe by default
    """

    def __init__(self, config: HTMLDocumentConfig | None = None):
        """Initialize the document.

        Args:
            config: Document configuration
        """
        self.config = config or HTMLDocumentConfig()

    def render(self, title: str = "", **context: Any) -> Markup:
        """Render the complete HTML document.

        Args:
            title: Document title
            **context: Additional context for subclass rendering

        Returns:
            Complete HTML document as Markup
        """
        parts: list[str] = []

        # DOCTYPE
        parts.append("<!DOCTYPE html>")

        # HTML open with lang
        parts.append(f'<html lang="{escape(self.config.lang)}">')

        # Head
        parts.append(self._render_head(title, **context))

        # Body
        parts.append(self._render_body(**context))

        # Close HTML
        parts.append("</html>")

        return Markup("\n".join(parts))

    def _render_head(self, title: str, **context: Any) -> str:
        """Render the head section."""
        parts: list[str] = []

        parts.append("<head>")

        # Charset (must be first)
        parts.append(f'<meta charset="{escape(self.config.charset)}">')

        # Viewport
        if self.config.viewport:
            parts.append(
                f'<meta name="viewport" content="{escape(self.config.viewport)}">',
            )

        # Title
        if title:
            parts.append(f"<title>{escape(title)}</title>")

        # Description
        if self.config.description:
            parts.append(
                f'<meta name="description" content="{escape(self.config.description)}">',
            )

        # Keywords
        if self.config.keywords:
            keywords = ", ".join(self.config.keywords)
            parts.append(f'<meta name="keywords" content="{escape(keywords)}">')

        # Author
        if self.config.author:
            parts.append(f'<meta name="author" content="{escape(self.config.author)}">')

        # Robots
        if self.config.robots:
            parts.append(f'<meta name="robots" content="{escape(self.config.robots)}">')

        # Theme color
        if self.config.theme_color:
            parts.append(
                f'<meta name="theme-color" content="{escape(self.config.theme_color)}">',
            )

        # Favicon
        if self.config.favicon:
            parts.append(
                f'<link rel="icon" type="{escape(self.config.favicon_type)}" href="{escape(self.config.favicon)}">',
            )

        # Open Graph tags
        if self.config.og_title:
            parts.append(
                f'<meta property="og:title" content="{escape(self.config.og_title)}">',
            )
        if self.config.og_description:
            parts.append(
                f'<meta property="og:description" content="{escape(self.config.og_description)}">',
            )
        if self.config.og_image:
            parts.append(
                f'<meta property="og:image" content="{escape(self.config.og_image)}">',
            )
        if self.config.og_url:
            parts.append(
                f'<meta property="og:url" content="{escape(self.config.og_url)}">',
            )
        if self.config.og_type:
            parts.append(
                f'<meta property="og:type" content="{escape(self.config.og_type)}">',
            )

        # Subclass head content (CSS, JS, etc.)
        head_content = self.render_head_content(**context)
        if head_content:
            parts.append(head_content)

        # Extra head content
        if self.config.extra_head:
            parts.append(self.config.extra_head)

        parts.append("</head>")

        return "\n".join(parts)

    def _render_body(self, **context: Any) -> str:
        """Render the body section."""
        parts: list[str] = []

        # Body open with attributes
        body_attrs = self.get_body_attributes(**context)
        if body_attrs:
            parts.append(f"<body {body_attrs}>")
        else:
            parts.append("<body>")

        # Body content from subclass
        body_content = self.render_body_content(**context)
        if body_content:
            parts.append(str(body_content))

        # Body end content (scripts, etc.)
        body_end = self.render_body_end(**context)
        if body_end:
            parts.append(body_end)

        parts.append("</body>")

        return "\n".join(parts)

    def get_body_attributes(self, **context: Any) -> str:
        """Get body element attributes.

        Override in subclasses to add classes, data attributes, etc.

        Returns:
            String of HTML attributes
        """
        return ""

    @abstractmethod
    def render_head_content(self, **context: Any) -> str:
        """Render content for the head section.

        Subclasses should implement this to add CSS links, inline styles, etc.

        Returns:
            HTML string for head section
        """

    @abstractmethod
    def render_body_content(self, **context: Any) -> str | Markup:
        """Render the main body content.

        Subclasses should implement this to render the page content.

        Returns:
            HTML string or Markup for body content
        """

    def render_body_end(self, **context: Any) -> str:
        """Render content at the end of body (before </body>).

        Subclasses can override to add scripts, etc.

        Returns:
            HTML string for body end
        """
        return ""


__all__ = ["HTMLDocument", "HTMLDocumentConfig"]
