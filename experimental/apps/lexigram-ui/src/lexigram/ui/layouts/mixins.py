"""Manager classes for layout CSS and JavaScript assets.

Provides composition-based asset management for layouts.
"""

from __future__ import annotations

from markupsafe import escape


class CSSManager:
    """Manages CSS asset injection for layout rendering."""

    def __init__(self) -> None:
        """Initialize CSS collections."""
        self._css_files: list[tuple[str, dict[str, str]]] = []
        self._inline_styles: list[str] = []

    def add_css(self, href: str, **attrs: str) -> None:
        """Add a CSS file link.

        Args:
            href: URL to CSS file
            **attrs: Additional attributes (media, crossorigin, etc.)
        """
        self._css_files.append((href, attrs))

    def add_inline_style(self, css: str) -> None:
        """Add inline CSS.

        Args:
            css: CSS rules
        """
        self._inline_styles.append(css)

    def render_css(self) -> str:
        """Render all CSS as HTML.

        Returns:
            HTML string with link and style tags
        """
        parts: list[str] = []

        # External CSS
        for href, attrs in self._css_files:
            attr_str = " ".join(f'{k}="{escape(v)}"' for k, v in attrs.items())
            if attr_str:
                parts.append(
                    f'<link rel="stylesheet" href="{escape(href)}" {attr_str}>',
                )
            else:
                parts.append(f'<link rel="stylesheet" href="{escape(href)}">')

        # Inline styles
        if self._inline_styles:
            parts.append("<style>")
            parts.extend(self._inline_styles)
            parts.append("</style>")

        return "\n".join(parts)


class JSManager:
    """Manages JavaScript asset injection for layout rendering."""

    def __init__(self) -> None:
        """Initialize JS collections."""
        self._js_files: list[tuple[str, dict[str, str]]] = []
        self._inline_scripts: list[str] = []
        self._deferred_scripts: list[str] = []

    def add_js(
        self,
        src: str,
        defer: bool = False,
        async_: bool = False,
        **attrs: str,
    ) -> None:
        """Add a JavaScript file.

        Args:
            src: URL to JS file
            defer: Add defer attribute
            async_: Add async attribute
            **attrs: Additional attributes
        """
        if defer:
            attrs["defer"] = ""
        if async_:
            attrs["async"] = ""
        self._js_files.append((src, attrs))

    def add_inline_script(self, script: str, defer: bool = False) -> None:
        """Add inline JavaScript.

        Args:
            script: JavaScript code
            defer: If True, render at end of body
        """
        if defer:
            self._deferred_scripts.append(script)
        else:
            self._inline_scripts.append(script)

    def render_js_head(self) -> str:
        """Render JS for head section.

        Returns:
            HTML string with script tags
        """
        parts: list[str] = []

        # External JS
        for src, attrs in self._js_files:
            attr_str = " ".join(
                f'{k}="{escape(v)}"' if v else k for k, v in attrs.items()
            )
            if attr_str:
                parts.append(f'<script src="{escape(src)}" {attr_str}></script>')
            else:
                parts.append(f'<script src="{escape(src)}"></script>')

        # Inline scripts (non-deferred)
        for script in self._inline_scripts:
            parts.append(f"<script>{script}</script>")

        return "\n".join(parts)

    def render_js_body_end(self) -> str:
        """Render deferred JS for end of body.

        Returns:
            HTML string with script tags
        """
        if not self._deferred_scripts:
            return ""

        parts = ["<script>"]
        parts.extend(self._deferred_scripts)
        parts.append("</script>")
        return "\n".join(parts)


__all__ = ["CSSManager", "JSManager"]
